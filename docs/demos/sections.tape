Output docs/demos/sections.gif

Set Width 1000
Set Height 900
Set FontSize 18
Set Padding 20
Set WindowBar Colorful
Set Theme { "name": "Karnes", "background": "#0c0a11", "foreground": "#e8e4ef", "selection": "#2a2533", "cursor": "#b210f2", "black": "#0c0a11", "red": "#f2546b", "green": "#4ade80", "yellow": "#facc15", "blue": "#60a5fa", "magenta": "#b210f2", "cyan": "#22d3ee", "white": "#e8e4ef", "brightBlack": "#6b6577", "brightRed": "#ff7a8c", "brightGreen": "#86efac", "brightYellow": "#fde047", "brightBlue": "#93c5fd", "brightMagenta": "#d062ff", "brightCyan": "#67e8f9", "brightWhite": "#ffffff" }

Hide
Type "PS1='$ ' && clear"
Enter
Show

Hide
Type `printf '# Structure\n\n<!-- fsg:start path=../src dirs-only -->\n<!-- fsg:end -->\n\n<!-- fsg:start path=../tests depth=1 summary fence=false -->\n<!-- fsg:end -->\n' > docs/structure.md && clear`
Enter
Show

Type "cat docs/structure.md"
Sleep 300ms
Enter
Sleep 2s

Type "fsg --update docs/structure.md"
Sleep 300ms
Enter
Sleep 2s

Type "clear && cat docs/structure.md"
Sleep 300ms
Enter
Sleep 4s

Hide
Type "rm docs/structure.md && clear"
Enter
