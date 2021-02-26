#include "ap_axi_sdata.h"
#include "ap_int.h"
#include "hls_stream.h"
#include "sizes.h"

#define DWIDTH 512
#define TDWIDTH 16

#ifndef HASH_UNITS
#define HASH_UNITS (cm_rows)
#endif

#ifndef PARALLELISATION
#define PARALLELISATION (HASH_UNITS)
#endif

// To be able to use macros within pragmas
// From https://www.xilinx.com/support/answers/46111.html
#define PRAGMA_SUB(x) _Pragma (#x)
#define DO_PRAGMA(x) PRAGMA_SUB(x)

typedef ap_axiu<DWIDTH, 1, 1, TDWIDTH> pkt;

// Sketch BRAM
#if defined(UNIVMON)
unsigned int cm_sketch_local[cm_rows][univmon_levels][cm_col_count];
#else
unsigned int cm_sketch_local[cm_rows][cm_col_count];
#endif

struct parallel_pkt {
  pkt pkts[PARALLELISATION];
};

unsigned int MurmurHash2(unsigned int key, int len, unsigned int seed)
{
#pragma HLS INLINE off
#pragma HLS pipeline II=1
  // Not inlining so that we can control the
  // amount of resources by hash unit count

  const unsigned char* data = (const unsigned char *)&key;
  const unsigned int m = 0x5bd1e995;
  unsigned int h = seed ^ len;
  switch(len) {
  case 3: h ^= data[2] << 16;
  case 2: h ^= data[1] << 8;
  case 1: h ^= data[0];
    h *= m;
  };
  h ^= h >> 13;
  h *= m;
  h ^= h >> 15;
  return h;
}

void update_sketch_util(hls::stream<parallel_pkt> &sketchIn,
                        hls::stream<parallel_pkt> &sketchOut) {
#pragma HLS INLINE off
#pragma HLS pipeline II=1

  if(!sketchIn.empty()){
    DO_PRAGMA(HLS ALLOCATION function instances=MurmurHash2 limit=HASH_UNITS)
    parallel_pkt batch = sketchIn.read();

    for(unsigned j = 0; j<PARALLELISATION; j++){
#pragma HLS UNROLL

      pkt curr = batch.pkts[j];
      unsigned key = curr.data(31, 0);
      // (39, 0) corresponds to packet counter (using as uniform random key currently)

#if defined(UNIVMON)
      unsigned level = __builtin_clz(MurmurHash2(key, 3, level_seeds[0]));
      if(level >= univmon_levels) {
        level = univmon_levels-1;
      }
#endif

    update_rows_loop: for(int row = 0; row < cm_rows; row++) {
#pragma HLS UNROLL

        unsigned hash = MurmurHash2(key, 3, cm_seeds[row]);
        unsigned index = hash % cm_col_count;

        // Not reusing arrays based on:
        // https://fling.seas.upenn.edu/~giesen/dynamic/wordpress/vivado-hls-learnings/

        // Sketch implementations
#if defined (COUNT_SKETCH)
        unsigned filter = MurmurHash2(key, 3, filter_seeds[row]) % 2;
        unsigned updated_value = cm_sketch_local[row][index] + 1 - 2*filter;
        cm_sketch_local[row][index] = updated_value;
#elif defined (UNIVMON)
        unsigned filter = MurmurHash2(key, 3, filter_seeds[row]) % 2;
        unsigned updated_value = cm_sketch_local[row][level][index] + 1 - 2*filter;
        cm_sketch_local[row][level][index] = updated_value;
#else
        unsigned updated_value = cm_sketch_local[row][index] + 1;
        cm_sketch_local[row][index] = updated_value;
#endif
      }
    }
    sketchOut.write(batch);
  }
}

void batch_pkts(hls::stream<pkt> &dataIn, hls::stream<parallel_pkt> &sketchIn) {
#pragma HLS INLINE off
#pragma HLS pipeline II=1

  /*
    Current limitation:
    All packets will be delivered if total elements
    in the stream is a multiple of PARALLELISATION
    If stream has packets less than PARALLELISATION
    then they would be stuck in the dataIn stream

    Fix:
    A fix would be a timeout, such that if packets don't arrive by
    a certain time then send a non full batch
  */

  if(!dataIn.empty()){
    // Ideally I would have used dataIn.full() check above
    // that would ensure that there are enough packets to batch
    // Apparently HLS does not support full() with read only streams
    // Hence, I am relying only on the blocking nature of read()
    parallel_pkt batch;
    for(unsigned j = 0; j<PARALLELISATION; j++){
      pkt curr = dataIn.read();
      batch.pkts[j] = curr;
    }
    sketchIn.write(batch);
  }
}

void unbatch_pkts(hls::stream<parallel_pkt> &sketchOut, hls::stream<pkt> &dataOut) {
#pragma HLS INLINE off
#pragma HLS pipeline II=1

  if(!sketchOut.empty()){
    parallel_pkt batch = sketchOut.read();
    for(unsigned j = 0; j<PARALLELISATION; j++){
      pkt curr = batch.pkts[j];
      dataOut.write(curr);
    }
  }
}

extern "C" {
  // sits between benchmark switch and network layer
  void update_sketch(hls::stream<pkt> &dataIn,
                     hls::stream<pkt> &dataOut) {
#pragma HLS DATAFLOW
#pragma HLS INTERFACE axis port=dataIn
#pragma HLS INTERFACE axis port=dataOut
    // free running kernel (always running, no need to start from host app)
#pragma HLS INTERFACE ap_ctrl_none port=return
#pragma HLS ARRAY_PARTITION variable = cm_sketch_local complete dim = 1

// #pragma HLS DATA_PACK variable=dataIn
// #pragma HLS DATA_PACK variable=dataOut

    // FIFO depth is controlled using connectivity.cfg
    // DO_PRAGMA(HLS STREAM variable=dataIn depth=PARALLELISATION)
    // DO_PRAGMA(HLS STREAM variable=dataOut depth=PARALLELISATION)

    static hls::stream<parallel_pkt> sketchIn;
#pragma HLS STREAM variable=sketchIn depth=16
#pragma HLS DATA_PACK variable=sketchIn

    static hls::stream<parallel_pkt> sketchOut;
#pragma HLS STREAM variable=sketchOut depth=16
#pragma HLS DATA_PACK variable=sketchOut

    // Currently this only works for 64B packets
    batch_pkts(dataIn, sketchIn);
    update_sketch_util(sketchIn, sketchOut);
    unbatch_pkts(sketchOut, dataOut);
  }

  void read_sketch(unsigned int* sketch_buf) {
#pragma HLS INTERFACE m_axi port=sketch_buf bundle=gmem offset=slave

#ifdef UNIVMON
  write_cm_sketch: for(unsigned iter = 0, level=0, row = 0, col = 0;
                       iter < cm_col_count * cm_rows * univmon_levels;
                       iter++, col++) {
#pragma HLS PIPELINE II=1
    if(col == cm_col_count) {
      col = 0;
      level++;
    }
    if(level == univmon_levels) {
      level = 0;
      row++;
    }
    sketch_buf[iter] = cm_sketch_local[row][level][col];
  }
#else
  write_cm_sketch: for(unsigned iter = 0, row = 0, col = 0;
                       iter < cm_col_count * cm_rows; iter++, col++) {
#pragma HLS PIPELINE II=1
      if(col == cm_col_count) {
        col = 0;
        row++;
      }
      sketch_buf[iter] = cm_sketch_local[row][col];
    }
  }
#endif
}

}
