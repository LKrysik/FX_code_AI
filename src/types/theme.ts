// Extend MUI theme to include custom trading colors
declare module '@mui/material/styles' {
  interface Palette {
    bullish: Palette['primary'];
    bearish: Palette['primary'];
    pump: Palette['primary'];
    dump: Palette['primary'];
  }

  interface PaletteOptions {
    bullish?: PaletteOptions['primary'];
    bearish?: PaletteOptions['primary'];
    pump?: PaletteOptions['primary'];
    dump?: PaletteOptions['primary'];
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