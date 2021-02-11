#include "ap_axi_sdata.h"
#include "ap_int.h"
#include "hls_stream.h"
#include "sizes.h"

#define DWIDTH 512
#define TDWIDTH 16

#ifndef HASH_UNITS
#define HASH_UNITS (cm_rows)
#endif

// To be able to use macros within pragmas
// From https://www.xilinx.com/support/answers/46111.html
#define PRAGMA_SUB(x) _Pragma (#x)
#define DO_PRAGMA(x) PRAGMA_SUB(x)

typedef ap_axiu<DWIDTH, 1, 1, TDWIDTH> pkt;
unsigned int cm_sketch_local[cm_rows][cm_col_count];

unsigned int MurmurHash2(unsigned int key, int len, unsigned int seed)
{
  // Not inlining so that we can control the
  // amount of resources by hash unit count
  #pragma HLS INLINE off
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

extern "C" {
  // sits between benchmark switch and network layer
  void update_sketch(hls::stream<pkt> &dataIn,
                     hls::stream<pkt> &dataOut) {
#pragma HLS DATAFLOW
#pragma HLS INTERFACE axis port=dataIn
#pragma HLS INTERFACE axis port=dataOut
#pragma HLS INTERFACE ap_ctrl_none port=return
#pragma HLS ARRAY_PARTITION variable = cm_sketch_local complete dim = 1

    pkt curr;
    unsigned int key;

    // Only works with 64 B packets right now
    if(!dataIn.empty()){
      DO_PRAGMA(HLS ALLOCATION function instances=MurmurHash2 limit=HASH_UNITS)
      dataIn.read(curr);

      // Short
      key = curr.data(31, 0);
      // (39, 0) corresponds to packet counter (using as uniform random key currently)

    update_rows_loop: for(int row = 0; row < cm_rows; row++) {
#pragma HLS UNROLL
        unsigned hash = MurmurHash2(key, 3, cm_seeds[row]);
        unsigned index = hash % cm_col_count;
        // Not reusing arrays based on: https://fling.seas.upenn.edu/~giesen/dynamic/wordpress/vivado-hls-learnings/
        unsigned updated_value = cm_sketch_local[row][index] + 1;
        cm_sketch_local[row][index] = updated_value;
      }

      dataOut.write(curr);
    }
  }

  void read_sketch(unsigned int* sketch_buf) {
#pragma HLS INTERFACE m_axi port=sketch_buf bundle=gmem offset=slave
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
}
