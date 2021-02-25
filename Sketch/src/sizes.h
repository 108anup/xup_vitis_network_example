#pragma once

#ifndef cm_rows
#define cm_rows 4
#endif

#ifndef cm_cols
#define cm_cols 12
#endif

#ifndef univmon_levels
#define univmon_levels 16
#endif

const unsigned int cm_col_count = (1 << cm_cols);
/*
  """
  Randomly generated numbers using python script
  """
  import random
  for i in range(12):
    print(hex(int(random.random()*(1<<32))))
 */
const unsigned int cm_seeds[] = {
    0xdbf60a44, 0xe8c413a4, 0xe8475470, 0x987d025c, 0x9d4fd14e, 0xdc5866fb,
    0x3fead523, 0x6e0b5c09, 0xf6b9b30b, 0xfd6dabc6, 0xba3eb757, 0xd1dd1308};

const unsigned int filter_seeds[] = {
    0xfc9f39dc, 0x18a00f0d, 0xee6d5b34, 0x5777a79,  0xb44817a9, 0xc55aaa47,
    0xf86727c7, 0x8d6c7d71, 0x3887b103, 0x6dd50a45, 0xdbd9d793, 0x7406b849};

const unsigned int level_seeds[] = {
    0xae6893e6, 0xd6a62748, 0x6ab3bdd8, 0x34d817fd, 0xacac1916, 0x6f2a7235,
    0x6cc88801, 0x4bf6c22d, 0x3a26e9d5, 0xb068ac69, 0x8e569e3a, 0x58eb6a24};
