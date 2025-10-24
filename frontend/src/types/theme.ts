import type { Palette as MuiPalette, PaletteOptions as MuiPaletteOptions } from '@mui/material/styles';

// Extend MUI theme to include custom trading colors
declare module '@mui/material/styles' {
  interface Palette {
    bullish: MuiPalette['primary'];
    bearish: MuiPalette['primary'];
    pump: MuiPalette['primary'];
    dump: MuiPalette['primary'];
  }

  interface PaletteOptions {
    bullish?: MuiPaletteOptions['primary'];
    bearish?: MuiPaletteOptions['primary'];
    pump?: MuiPaletteOptions['primary'];
    dump?: MuiPaletteOptions['primary'];
  }
}

declare module '@mui/material/Chip' {
  interface ChipPropsColorOverrides {
    bullish: true;
    bearish: true;
    pump: true;
    dump: true;
  }
}

declare module '@mui/material/Button' {
  interface ButtonPropsColorOverrides {
    bullish: true;
    bearish: true;
    pump: true;
    dump: true;
  }
}
