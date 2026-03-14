import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // set-state-in-effect: Viele Komponenten syncen State aus Props/URL – pragmatisch deaktiviert
      'react-hooks/set-state-in-effect': 'off',
      // PipelineStore exportiert Provider + Hook – Fast Refresh Einschränkung akzeptiert
      'react-refresh/only-export-components': 'warn',
    },
  },
])
