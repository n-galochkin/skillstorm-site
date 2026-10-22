/* The archipelago, in one place: the site's route, its chapters and its map legend
   all read from this. Positions are metres on the sea plane, x east, z south.
   Each island has a shape and a feature, so none of them reads like another. */

export const ISLANDS = [
  {
    id: 'landing',
    name: { ru: 'Берег', en: 'The Shore' },
    pos: [0, 0], radius: 26, height: 9, seed: 11,
    shape: 'plateau', terraces: 3,
    trees: 9, spires: 4, feature: 'pier', boats: 3,
  },
  {
    id: 'combat',
    name: { ru: 'Бой', en: 'The Fight' },
    pos: [86, 34], radius: 30, height: 9, seed: 23,
    shape: 'plateau', terraces: 3,
    trees: 10, spires: 7, arena: true, boats: 2,
  },
  {
    id: 'skills',
    name: { ru: 'Навыки', en: 'Skills' },
    pos: [168, -26], radius: 27, height: 11, seed: 37,
    shape: 'ridge', terraces: 4,
    trees: 20, spires: 5, feature: 'ruins',
  },
  {
    id: 'storm',
    name: { ru: 'Шторм', en: 'The Storm' },
    pos: [244, 44], radius: 29, height: 12, seed: 51,
    shape: 'volcano', terraces: 4, grass: 0x5f9a3f,
    trees: 11, spires: 6, feature: 'volcano', storm: true,
  },
  {
    id: 'forge',
    name: { ru: 'Кузня', en: 'The Forge' },
    pos: [330, -18], radius: 31, height: 9, seed: 67,
    shape: 'plateau', terraces: 3,
    trees: 12, spires: 4, feature: 'village',
  },
  {
    id: 'devlog',
    name: { ru: 'Верфь', en: 'The Yard' },
    pos: [410, 40], radius: 25, height: 8, seed: 83,
    shape: 'plateau', terraces: 3,
    trees: 8, spires: 3, feature: 'pier', boats: 2,
  },
];

/* Islets that are only there to make the sea feel inhabited. */
export const ISLETS = [
  { id: 'islet_01', pos: [44, -58], radius: 9, height: 9, seed: 101, shape: 'peak', snowline: 7.5, terraces: 3, trees: 3, spires: 3 },
  { id: 'islet_02', pos: [128, 66], radius: 7, height: 5, seed: 113, shape: 'plateau', terraces: 2, trees: 2, spires: 2 },
  { id: 'islet_03', pos: [206, -70], radius: 11, height: 6.5, seed: 127, shape: 'plateau', terraces: 3, trees: 4, spires: 3 },
  { id: 'islet_04', pos: [290, 84], radius: 8, height: 8, seed: 131, shape: 'volcano', terraces: 3, trees: 2, spires: 2 },
  { id: 'islet_05', pos: [372, 74], radius: 10, height: 6, seed: 149, shape: 'plateau', terraces: 2, trees: 4, spires: 2 },
  { id: 'islet_06', pos: [58, 92], radius: 6, height: 4.5, seed: 157, shape: 'plateau', terraces: 2, trees: 1, spires: 2 },
  { id: 'islet_07', pos: [300, -74], radius: 7, height: 10, seed: 163, shape: 'peak', snowline: 8, terraces: 3, trees: 2, spires: 2 },
  { id: 'islet_08', pos: [455, -36], radius: 12, height: 7, seed: 173, shape: 'plateau', terraces: 3, trees: 5, spires: 3 },
];
