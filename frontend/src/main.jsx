import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider, createGlobalStyle } from 'styled-components'
import App from './App'
import { theme } from './theme'

const GlobalStyle = createGlobalStyle`
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Pretendard', -apple-system, sans-serif;
    background: ${({ theme }) => theme.bgSoft};
    color: ${({ theme }) => theme.text};
  }
  button { font-family: inherit; cursor: pointer; }
  input, select { font-family: inherit; }
`

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <GlobalStyle />
      <App />
    </ThemeProvider>
  </React.StrictMode>,
)
