import { createTheme, alpha, lighten, darken } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    primary: {
      lighter: lighten('#1976d2', 0.85),
      light: '#4791db',
      main: '#1976d2',
      dark: '#115293',
      darker: darken('#1976d2', 0.2),
      contrastText: '#fff',
    },
    secondary: {
      lighter: lighten('#4caf50', 0.85),
      light: '#80e27e',
      main: '#4caf50',
      dark: '#087f23',
      darker: darken('#4caf50', 0.2),
      contrastText: '#fff',
    },
    error: {
      lighter: lighten('#f44336', 0.85),
      light: '#e57373',
      main: '#f44336',
      dark: '#d32f2f',
      darker: darken('#f44336', 0.2),
      contrastText: '#fff',
    },
    warning: {
      lighter: lighten('#ff9800', 0.85),
      light: '#ffb74d',
      main: '#ff9800',
      dark: '#f57c00',
      darker: darken('#ff9800', 0.2),
      contrastText: 'rgba(0, 0, 0, 0.87)',
    },
    info: {
      lighter: lighten('#03a9f4', 0.85),
      light: '#4fc3f7',
      main: '#03a9f4',
      dark: '#0288d1',
      darker: darken('#03a9f4', 0.2),
      contrastText: '#fff',
    },
    success: {
      lighter: lighten('#4caf50', 0.85),
      light: '#81c784',
      main: '#4caf50',
      dark: '#388e3c',
      darker: darken('#4caf50', 0.2),
      contrastText: 'rgba(0, 0, 0, 0.87)',
    },
    grey: {
      50: '#fafafa',
      100: '#f5f5f5',
      200: '#eeeeee',
      300: '#e0e0e0',
      400: '#bdbdbd',
      500: '#9e9e9e',
      600: '#757575',
      700: '#616161',
      800: '#424242',
      900: '#212121',
      A100: '#d5d5d5',
      A200: '#aaaaaa',
      A400: '#303030',
      A700: '#616161',
    },
    background: {
      default: '#f5f7fa',
      paper: '#ffffff',
    },
    text: {
      primary: 'rgba(0, 0, 0, 0.87)',
      secondary: 'rgba(0, 0, 0, 0.6)',
      disabled: 'rgba(0, 0, 0, 0.38)',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
      '"Apple Color Emoji"',
      '"Segoe UI Emoji"',
      '"Segoe UI Symbol"',
    ].join(','),
    h1: {
      fontSize: 'clamp(2rem, 5vw, 2.5rem)',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: 'clamp(1.75rem, 4vw, 2rem)',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h3: {
      fontSize: 'clamp(1.5rem, 3vw, 1.75rem)',
      fontWeight: 600,
      lineHeight: 1.2,
    },
    h4: {
      fontSize: 'clamp(1.25rem, 2.5vw, 1.5rem)',
      fontWeight: 700,
      lineHeight: 1.2,
    },
    h5: {
      fontSize: 'clamp(1.1rem, 2vw, 1.25rem)',
      fontWeight: 600,
      lineHeight: 1.2,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.2,
    },
    subtitle1: {
      fontSize: '1.1rem',
      fontWeight: 500,
      lineHeight: 1.5,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.5,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.57,
    },
    button: {
      fontWeight: 600,
      textTransform: 'none',
    },
    caption: {
      fontSize: '0.75rem',
      fontWeight: 400,
      lineHeight: 1.5,
    },
  },
  shape: {
    borderRadius: 8,
  },
  shadows: [
    'none',
    '0px 2px 1px -1px rgba(0,0,0,0.1),0px 1px 1px 0px rgba(0,0,0,0.07),0px 1px 3px 0px rgba(0,0,0,0.06)',
    '0px 3px 1px -2px rgba(0,0,0,0.1),0px 2px 2px 0px rgba(0,0,0,0.07),0px 1px 5px 0px rgba(0,0,0,0.06)',
    '0px 3px 3px -2px rgba(0,0,0,0.1),0px 3px 4px 0px rgba(0,0,0,0.07),0px 1px 8px 0px rgba(0,0,0,0.06)',
    '0px 2px 4px -1px rgba(0,0,0,0.1),0px 4px 5px 0px rgba(0,0,0,0.07),0px 1px 10px 0px rgba(0,0,0,0.06)',
    '0px 3px 5px -1px rgba(0,0,0,0.1),0px 5px 8px 0px rgba(0,0,0,0.07),0px 1px 14px 0px rgba(0,0,0,0.06)',
    '0px 3px 5px -1px rgba(0,0,0,0.1),0px 6px 10px 0px rgba(0,0,0,0.07),0px 1px 18px 0px rgba(0,0,0,0.06)',
    '0px 4px 5px -2px rgba(0,0,0,0.1),0px 7px 10px 1px rgba(0,0,0,0.07),0px 2px 16px 1px rgba(0,0,0,0.06)',
    '0px 5px 5px -3px rgba(0,0,0,0.1),0px 8px 10px 1px rgba(0,0,0,0.07),0px 3px 14px 2px rgba(0,0,0,0.06)',
    '0px 5px 6px -3px rgba(0,0,0,0.1),0px 9px 12px 1px rgba(0,0,0,0.07),0px 3px 16px 2px rgba(0,0,0,0.06)',
    '0px 6px 6px -3px rgba(0,0,0,0.1),0px 10px 14px 1px rgba(0,0,0,0.07),0px 4px 18px 3px rgba(0,0,0,0.06)',
    '0px 6px 7px -4px rgba(0,0,0,0.1),0px 11px 15px 1px rgba(0,0,0,0.07),0px 4px 20px 3px rgba(0,0,0,0.06)',
    '0px 7px 8px -4px rgba(0,0,0,0.1),0px 12px 17px 2px rgba(0,0,0,0.07),0px 5px 22px 4px rgba(0,0,0,0.06)',
    '0px 7px 8px -4px rgba(0,0,0,0.1),0px 13px 19px 2px rgba(0,0,0,0.07),0px 5px 24px 4px rgba(0,0,0,0.06)',
    '0px 7px 9px -4px rgba(0,0,0,0.1),0px 14px 21px 2px rgba(0,0,0,0.07),0px 5px 26px 4px rgba(0,0,0,0.06)',
    '0px 8px 9px -5px rgba(0,0,0,0.1),0px 15px 22px 2px rgba(0,0,0,0.07),0px 6px 28px 5px rgba(0,0,0,0.06)',
    '0px 8px 10px -5px rgba(0,0,0,0.1),0px 16px 24px 2px rgba(0,0,0,0.07),0px 6px 30px 5px rgba(0,0,0,0.06)',
    '0px 8px 11px -5px rgba(0,0,0,0.1),0px 17px 26px 2px rgba(0,0,0,0.07),0px 6px 32px 5px rgba(0,0,0,0.06)',
    '0px 9px 11px -5px rgba(0,0,0,0.1),0px 18px 28px 2px rgba(0,0,0,0.07),0px 7px 34px 6px rgba(0,0,0,0.06)',
    '0px 9px 12px -6px rgba(0,0,0,0.1),0px 19px 29px 2px rgba(0,0,0,0.07),0px 7px 36px 6px rgba(0,0,0,0.06)',
    '0px 10px 13px -6px rgba(0,0,0,0.1),0px 20px 31px 3px rgba(0,0,0,0.07),0px 8px 38px 7px rgba(0,0,0,0.06)',
    '0px 10px 13px -6px rgba(0,0,0,0.1),0px 21px 33px 3px rgba(0,0,0,0.07),0px 8px 40px 7px rgba(0,0,0,0.06)',
    '0px 10px 14px -6px rgba(0,0,0,0.1),0px 22px 35px 3px rgba(0,0,0,0.07),0px 8px 42px 7px rgba(0,0,0,0.06)',
    '0px 11px 14px -7px rgba(0,0,0,0.1),0px 23px 36px 3px rgba(0,0,0,0.07),0px 9px 44px 8px rgba(0,0,0,0.06)',
    '0px 11px 15px -7px rgba(0,0,0,0.1),0px 24px 38px 3px rgba(0,0,0,0.07),0px 9px 46px 8px rgba(0,0,0,0.06)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
          margin: 0,
          padding: 0,
        },
        html: {
          width: '100%',
          height: '100%',
          WebkitOverflowScrolling: 'touch',
        },
        body: {
          width: '100%',
          height: '100%',
        },
        '#root': {
          width: '100%',
          height: '100%',
        },
        'input[type=number]': {
          MozAppearance: 'textfield',
          '&::-webkit-outer-spin-button': {
            margin: 0,
            WebkitAppearance: 'none',
          },
          '&::-webkit-inner-spin-button': {
            margin: 0,
            WebkitAppearance: 'none',
          },
        },
        img: {
          maxWidth: '100%',
          display: 'block',
          height: 'auto',
        },
      },
    },
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          padding: '8px 16px',
          '&.MuiButton-contained': {
            '&:hover': {
              boxShadow: '0 8px 16px 0 rgba(0,0,0,0.1)',
            },
          },
          '&.MuiButton-outlined': {
            '&:hover': {
              backgroundColor: alpha('#1976d2', 0.04),
            },
          },
        },
        sizeLarge: {
          padding: '11px 24px',
        },
        sizeSmall: {
          padding: '6px 16px',
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          padding: 8,
          borderRadius: 8,
          '&:hover': {
            backgroundColor: alpha('#000', 0.04),
          },
        },
        sizeSmall: {
          padding: 4,
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 0 2px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.06)',
          transition: 'box-shadow 200ms cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            boxShadow: '0 12px 24px -4px rgba(0,0,0,0.12)',
          },
        },
      },
    },
    MuiCardContent: {
      styleOverrides: {
        root: {
          padding: 24,
          '&:last-child': {
            paddingBottom: 24,
          },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: '1px solid',
          borderColor: alpha('#000', 0.08),
        },
        head: {
          fontWeight: 600,
          backgroundColor: alpha('#000', 0.02),
          color: theme => theme.palette.text.primary,
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:last-child td': {
            borderBottom: 0,
          },
          '&.MuiTableRow-hover:hover': {
            backgroundColor: alpha('#000', 0.02),
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          fontWeight: 500,
        },
        sizeSmall: {
          height: 24,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          borderRadius: 12,
        },
        elevation1: {
          boxShadow: '0 0 2px 0 rgba(0,0,0,0.12), 0 2px 4px -1px rgba(0,0,0,0.06)',
        },
        elevation2: {
          boxShadow: '0 0 2px 0 rgba(0,0,0,0.12), 0 4px 8px -2px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            '&:hover fieldset': {
              borderColor: theme => theme.palette.primary.main,
            },
            '&.Mui-focused fieldset': {
              borderWidth: 2,
            },
          },
        },
      },
    },
    MuiCircularProgress: {
      styleOverrides: {
        root: {
          color: theme => theme.palette.primary.main,
        },
      },
    },
    MuiSkeleton: {
      defaultProps: {
        animation: 'wave',
      },
      styleOverrides: {
        root: {
          backgroundColor: alpha('#000', 0.08),
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          overflow: 'hidden',
        },
      },
    },
  },
});

export default theme;