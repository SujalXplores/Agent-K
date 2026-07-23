import { Color } from "three";

export const NODE_POSITIONS = [
  [-3.6, 1.8, -0.8],
  [-2.1, 0.8, 0.2],
  [-3.1, -1.4, -0.3],
  [-0.8, 2, 0.4],
  [0.2, 0.7, -0.2],
  [0, -1, 0.45],
  [2.2, 1.6, -0.5],
  [2.9, 0, 0.15],
  [2, -1.8, -0.4],
  [4, 1, 0.35],
  [4.1, -1.2, -0.2],
] as const;

export const NETWORK_EDGES = [
  [0, 1], [0, 3], [1, 2], [1, 4], [2, 5], [3, 4],
  [3, 6], [4, 5], [4, 6], [4, 7], [5, 8], [6, 7],
  [6, 9], [7, 8], [7, 9], [7, 10], [8, 10],
] as const;

export const NETWORK_COLORS = {
  blue: new Color("#3897ff"),
  coral: new Color("#ff5047"),
  dim: new Color("#33415d"),
  green: new Color("#46d878"),
} as const;

export const ROOT_NODE = 5;