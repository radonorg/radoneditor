import curses
import sys
from pygments import highlight
from pygments.lexers import PythonLexer  # Replace with the desired language
from pygments.token import Token
from pygments.formatters.terminal256 import Terminal256Formatter
from pygments.styles import get_style_by_name

class CursesFormatter(Terminal256Formatter):
    """Custom formatter to extract tokens and their styles for curses."""
    def __init__(self):
        super().__init__()
        self.tokens = []

    def format(self, tokensource, outfile):
        for ttype, value in tokensource:
            self.tokens.append((ttype, value))

class SimpleVim:
    def __init__(self, stdscr, filename=None):
        self.stdscr = stdscr
        self.style = get_style_by_name("monokai")
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Default
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Keywords
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Names
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Strings
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK)  # Comments
        curses.init_pair(6, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Operators
        curses.init_pair(7, curses.COLOR_RED, curses.COLOR_BLACK)    # Punctuation
        curses.init_pair(8, curses.COLOR_BLUE, curses.COLOR_BLACK)   # Numbers
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_WHITE)
        self.filename = filename
        self.text = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.R, self.C = stdscr.getmaxyx()
        self.mode = 'NORMAL'
        self.command_input = ''
        self.old_cursor_x = 0  # Cached previous cursor position (for prevention of flickering)
        self.old_cursor_y = 0
        self.modified = 0
        self.status = "hello world"
        self.scroll_offset = 0  # Number of lines to scroll (vertical offset)

        # Load the file content if a filename is provided
        if filename:
            self.load_file(filename)
        else:
            self.text = [[""]]  # Initialize with one empty line

    def print_status_bar(self):
        self.status = ""
        self.status += self.filename + " - " + str(len(self.text)) + " lines"
        if self.modified:
            self.status += " modified"
        else:
            self.status += " saved"    
        pos = " Row " + str(self.cursor_y+1) + ", Col " + str(self.cursor_x)
        space = self.stdscr.getmaxyx()[1] - len(self.status) - len(pos) - 3
        for i in range(space) :
            self.status += " "
        self.status += pos + " "
        return self.status
    
    def load_file(self, filename):
        """Load the content of the file into the editor."""
        try:
            with open(filename) as f:
                cont = f.read().split("\n")
                for rw in cont[:-1]:
                    self.text.append([ord(c) for c in rw])
        except FileNotFoundError:
            self.text.append([])
        except IOError:
            self.text = [f"Error: Unable to open {filename}.\n"]
    
    def save_file(self):
        """Save the current content to the file."""
        if self.filename:
            with open(self.filename, 'w') as file:
                for line in self.text:
                    file.write(''.join(chr(c) for c in line) + "\n")
        self.modified = 0
    
    def draw(self):
        """Render the content of the editor with syntax highlighting."""
        self.stdscr.clear()
        
        # Combine 2D text array into strings for each line
        text_lines = ["".join(chr(c) for c in line) for line in self.text]
        
        # Get the visible portion of the text
        visible_lines = text_lines[self.scroll_offset:self.scroll_offset + self.stdscr.getmaxyx()[0] - 1]
        
        # Use Pygments to tokenize the visible portion
        code = "\n".join(visible_lines)
        formatter = CursesFormatter()
        highlight(code, PythonLexer(), formatter)
        
        # Map Pygments tokens to curses color pairs
        token_colors = {
            Token.Keyword: curses.color_pair(2),
            Token.Name: curses.color_pair(3),
            Token.String: curses.color_pair(4),
            Token.Comment: curses.color_pair(5),
            Token.Operator: curses.color_pair(6),
            Token.Punctuation: curses.color_pair(7),
            Token.Number: curses.color_pair(8),
        }
        
        # Render the visible lines
        y = 0  # Start rendering at the top of the screen
        x = 0  # Horizontal cursor for each line
        
        for ttype, value in formatter.tokens:
            color = token_colors.get(ttype, curses.color_pair(1))  # Default color pair
            for char in value:
                if char == "\n":  # Handle line breaks
                    y += 1
                    x = 0
                    if y >= self.stdscr.getmaxyx()[0] - 1:  # Stop rendering if out of vertical bounds
                        break
                else:
                    if 0 <= y < self.stdscr.getmaxyx()[0] - 1 and 0 <= x < self.stdscr.getmaxyx()[1] - 1:
                        try:
                            self.stdscr.addch(y, x, char, color)
                        except curses.error:
                            pass
                    x += 1
            if y >= self.stdscr.getmaxyx()[0] - 1:
                break
        
        # Display mode or status at the bottom
        self.print_status_bar()
        self.stdscr.addstr(self.stdscr.getmaxyx()[0] - 1, 0, self.status[:self.stdscr.getmaxyx()[1] - 1], curses.color_pair(9))
        
        # Adjust cursor position for scrolling
        cursor_display_y = self.cursor_y - self.scroll_offset
        if 0 <= cursor_display_y < self.stdscr.getmaxyx()[0] - 1:
            self.stdscr.move(cursor_display_y, min(self.cursor_x, self.stdscr.getmaxyx()[1] - 1))
        
        # Refresh screen
        self.stdscr.refresh()



    def handle_input(self):
        """Handle user input."""
        key = self.stdscr.getch()
        height, width = self.stdscr.getmaxyx()  # Get screen dimensions
        total_lines = len(self.text)  # Track the total number of lines

        def ctrl(c):
            return c & 0x1f

        if key == ctrl(ord("q")):  # Quit
            return False
        elif key == ctrl(ord("s")):  # Save file
            self.save_file()
        elif key in (curses.KEY_BACKSPACE, 8):  # Backspace
            if self.cursor_x > 0:
                self.cursor_x -= 1
                del self.text[self.cursor_y][self.cursor_x]
            elif self.cursor_x == 0 and self.cursor_y > 0:
                prev_line = self.text[self.cursor_y - 1]
                current_line = self.text[self.cursor_y]
                self.cursor_x = len(prev_line)
                prev_line.extend(current_line)
                del self.text[self.cursor_y]
                self.cursor_y -= 1

            self.modified += 1

        elif key == curses.KEY_UP:  # Up arrow
            if self.cursor_y > 0:
                self.cursor_y -= 1
                if self.cursor_y < self.scroll_offset:  # Scroll up
                    self.scroll_offset -= 1
        elif key == curses.KEY_DOWN:  # Down arrow
            if self.cursor_y < total_lines - 1:  # Prevent moving beyond the last line
                self.cursor_y += 1
                if self.cursor_y >= self.scroll_offset + height - 1:  # Scroll down
                    self.scroll_offset += 1
            elif self.cursor_y == total_lines - 1:  # At the last line
                # Prevent scrolling further
                self.scroll_offset = max(0, total_lines - height + 1)
        elif key == curses.KEY_LEFT:  # Left arrow
            if self.cursor_x > 0:
                self.cursor_x -= 1
        elif key == curses.KEY_RIGHT:  # Right arrow
            if self.cursor_x < len(self.text[self.cursor_y]):
                self.cursor_x += 1
        elif key == 10:  # Enter key (newline)
            # Split the current line at the cursor position
            current_line = self.text[self.cursor_y]
            new_line = current_line[self.cursor_x:]  # The part after the cursor
            self.text[self.cursor_y] = current_line[:self.cursor_x]  # The part before the cursor
            self.text.insert(self.cursor_y + 1, new_line)  # Insert the new line after the current line
            self.cursor_y += 1  # Move the cursor down to the new line
            self.cursor_x = 0  # Move the cursor to the start of the new line
            self.modified += 1
        elif 32 <= key <= 126:  # Printable ASCII characters
            # Insert character into text
            if self.cursor_x == len(self.text[self.cursor_y]):  # If at the end of the current line
                self.text[self.cursor_y].append(key)  # Append to the current line
            else:
                self.text[self.cursor_y].insert(self.cursor_x, key)  # Insert at the cursor position
            self.cursor_x += 1
            self.modified += 1
        else:
            pass  # Ignore other keys

        return True


    def run(self):
        """Main loop to run the editor."""
        while True:
            self.draw()
            if not self.handle_input():
                break


def main(stdscr):
    # Get filename from command-line argument if provided
    filename = None
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    
    # Initialize the SimpleVim instance with the filename (if any)
    editor = SimpleVim(stdscr, filename)
    editor.run()

# Initialize curses application
curses.wrapper(main)
