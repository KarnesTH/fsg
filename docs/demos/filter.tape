Output docs/demos/filter.gif

Set Width 1000
Set Height 560
Set FontSize 18
Set Padding 20
Set WindowBar Colorful
Set Theme { "name": "Karnes", "background": "#0c0a11", "foreground": "#e8e4ef", "selection": "#2a2533", "cursor": "#b210f2", "black": "#0c0a11", "red": "#f2546b", "green": "#4ade80", "yellow": "#facc15", "blue": "#60a5fa", "magenta": "#b210f2", "cyan": "#22d3ee", "white": "#e8e4ef", "brightBlack": "#6b6577", "brightRed": "#ff7a8c", "brightGreen": "#86efac", "brightYellow": "#fde047", "brightBlue": "#93c5fd", "brightMagenta": "#d062ff", "brightCyan": "#67e8f9", "brightWhite": "#ffffff" }

Hide
Type "PS1='$ ' && clear"
Enter
Show

Type `fsg --include "*.py" --exclude tests --depth 3 --no-fence`
Sleep 300ms
Enter
Sleep 3s

Type "clear && fsg --dirs-only --no-fence"
Sleep 300ms
Enter
Sleep 3s
