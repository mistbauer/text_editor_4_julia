from tkinter import *
from tkinter.filedialog import askopenfilename, asksaveasfilename
import subprocess, re
import tkinter as tk
import sys

window = Tk()
window.title('Julia IDE')

gpath = ''


class TextLineNumbers(tk.Canvas):
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        self.textwidget = text_widget

    def redraw(self, *args):
        self.delete("all")

        i = self.textwidget.index("@0,0")
        while True:
            dline = self.textwidget.dlineinfo(i)
            if dline is None: break
            y = dline[1]
            linenum = str(i).split(".")[0]
            self.create_text(2, y, anchor="nw", text=linenum)
            i = self.textwidget.index("%s+1line" % i)


class CustomText(tk.Text):
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        self._orig = self._w + "_orig"
        self.tk.call("rename", self._w, self._orig)
        self.tk.createcommand(self._w, self._proxy)

    def _proxy(self, *args):
        cmd = (self._orig,) + args
        result = self.tk.call(cmd)

        if (args[0] in ("insert", "replace", "delete") or
                args[0:3] == ("mark", "set", "insert") or
                args[0:2] == ("xview", "moveto") or
                args[0:2] == ("xview", "scroll") or
                args[0:2] == ("yview", "moveto") or
                args[0:2] == ("yview", "scroll")
        ):
            self.event_generate("<<Change>>", when="tail")

        return result


class TextEditorIDE(tk.Frame):
    def __init__(self, *args, **kwargs):
        self.callback = kwargs.pop("autocomplete", None)
        tk.Frame.__init__(self, *args, **kwargs)
        self.text = CustomText(self)
        self.vsb = tk.Scrollbar(orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=self.vsb.set)
        self.text.tag_configure("bigfont", font=("Helvetica", "24", "bold"))
        self.text.tag_configure("match_func", foreground="yellow")
        self.text.tag_configure("match_oper", foreground="red")
        self.linenumbers = TextLineNumbers(self, width=30)
        self.linenumbers.attach(self.text)

        self.vsb.pack(side="right", fill="y")
        self.linenumbers.pack(side="left", fill="y")
        self.text.pack(side="right", fill="both", expand=True)

        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)
        self.text.bind("<Any-KeyRelease>", self._autocomplete)
        self.text.bind("<Tab>", self._handle_tab)

        self.text.config(bg='#362f2e', fg='#d2ded1', insertbackground='white')

        self.checked = tk.BooleanVar()


    def _handle_tab(self, event):
        tag_ranges = self.text.tag_ranges("autocomplete")
        if tag_ranges:
            self.text.mark_set("insert", tag_ranges[1])
            self.text.tag_remove("sel", "1.0", "end")
            self.text.tag_remove("autocomplete", "1.0", "end")
            return "break"

    def _autocomplete(self, event):
        if event.char and self.callback and event.keysym != "BackSpace":
            word = self.text.get("insert-1c wordstart", "insert-1c wordend")
            matches = self.callback(word)
            if matches:
                remainder = matches[0][len(word):]
                insert = self.text.index("insert")
                self.text.insert(insert, remainder, ("sel", "autocomplete"))
                self.text.mark_set("insert", insert)

    def _on_change(self, event):
        self.linenumbers.redraw()

    def runCode(self):
        global gpath
        self.saveFileAs()
        with open(gpath, 'r') as file:
            code = file.read()
            self.text.delete('1.0', END)
            self.text.insert('1.0', code)
        output.delete('1.0', END)
        if gpath == '':
            saveMsg = Toplevel()
            msg = Label(saveMsg, text="Please save the file first")
            msg.pack()
            return
        command = f'julia {gpath}'
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        outputResult, error = process.communicate()
        output.insert('1.0', outputResult)
        output.insert('1.0', error)

    def Dark_theme(self):
        if self.checked.get() == True:
            self.text.tag_configure("match_func", foreground="blue")
            self.text.config(bg='#ffffff', fg='#000000', insertbackground='black')
            output.config(bg='#ffffff', fg='#000000')
        elif self.checked.get() == False:
            self.text.tag_configure("match_func", foreground="yellow")
            self.text.config(bg='#362f2e', fg='#d2ded1', insertbackground='white')
            output.config(bg='#362f2e', fg='#1dd604')

    def openFile(self):
        path = askopenfilename(filetypes=[('Julia Files', '*.jl')])
        with open(path, 'r') as file:
            code = file.read()
            self.text.delete('1.0', END)
            self.text.insert('1.0', code)
            global gpath
            gpath = path

    def saveFileAs(self):
        global gpath
        if gpath == '':
            path = asksaveasfilename(filetypes=[('Julia Files', '*.jl')])
        else:
            path = gpath
        with open(path, 'w') as file:
            code = self.text.get('1.0', END)
            file.write(code)
        gpath = path

    def highlight(self, tag, start, end):
        self.text.tag_add(tag, start, end)

    def highlight_all(self, pattern, tag):
        for elem in pattern:
            for match in self.search_re(elem):
                self.highlight(tag, match[0], match[1])

    def clean_highlights(self, tag):
        self.text.tag_remove(tag, "1.0", tk.END)

    def search_re(self, pattern):
        matches = []
        text = self.text.get("1.0", tk.END).splitlines()
        for i, line in enumerate(text):
            for match in re.finditer(pattern, line):
                matches.append((f"{i + 1}.{match.start()}", f"{i + 1}.{match.end()}"))

        return matches

    def highlight_pattern(self, pattern, tag):
        self.clean_highlights(tag)
        self.highlight_all(pattern, tag)


def get_matches(word):
    words = ["False", "else", "None", "break", "except", "in", "raise", "for", "function", "True", "class", "return",
             "and", "continue", "as", "def", "from", "while", "del", "global", "not", "with", "elif", "if", "or",
             "yield", "abs", "all", "any", "bool", "float", "input", "int", "len", "list", "locals", "map", "max",
             "min", "next", "object", "open", "pow", "print", "range", "end", "return", "round", "set", "str", "sum",
             "sin", "cos", "super", "tuple", "typeof", "import", "using"]
    matches = [x for x in words if x.startswith(word)]
    return matches


def highlight_text(args):
    Editor.highlight_pattern(
        [r"float\b", r"input\b", r"int\b", r"len\b", r"list\b", r"locals\b", r"map\b", r"max\b", r"min\b",
         r"open\b", r"pow\b", r"print\b", r"println\b", r"range\b", r"return\b", r"round\b", r"set\b", r"str\b",
         r"sum\b", r"typeof\b", r"\bsin\b", r"\bcos\b",
         r"import\b", r"abs\b", r"using\b"], "match_func"
    )
    Editor.highlight_pattern(
        [r"False\b", r"else\b", r"None\b", r"break\b", r"except\b", r"\bin\b", r"raise\b", r"for\b", r"function\b",
         r"True\b", r"class\b", r"\band\b",
         r"continue\b", r"as\b", r"def\b", r"from\b", r"while\b", r"del\b", r"global\b", r"not\b", r"with\b", r"elif\b",
         r"if\b", r"or\b", r"yield\b",
         r"all\b", r"any\b", r"bool\b", r"next\b", r"object\b",
         r"\bend\b", r"super\b", r"tuple\b"], "match_oper"
    )


Editor = TextEditorIDE(window, autocomplete=get_matches)
Editor.pack(side="top", fill="both", expand=True)
Editor.text.bind("<KeyPress>", highlight_text)

output = CustomText()
output.config(bg='#362f2e', fg='#1dd604')
output.pack(side="right", fill="both", expand=True)

menuBar = Menu(window)

fileBar = Menu(menuBar, tearoff=0)
fileBar.add_command(label='Открыть файл', command=Editor.openFile)
fileBar.add_command(label='Сохранить файл', command=Editor.saveFileAs)
fileBar.add_command(label='Сохранить файл как', command=Editor.saveFileAs)
fileBar.add_separator()
fileBar.add_command(label='Выйти', command=sys.exit)
menuBar.add_cascade(label='Файл', menu=fileBar)

menuBar.add_command(label='Запустить', command=Editor.runCode)

optionsBar = Menu(menuBar, tearoff=0)
optionsBar.add_checkbutton(label='Светлая тема', onvalue=True, offvalue=False, variable=Editor.checked, command=Editor.Dark_theme)
menuBar.add_cascade(label='Настройки', menu=optionsBar)

menuBar.add_command(label='О программе')
menuBar.add_command(label='Помощь')

window.config(menu=menuBar)
window.mainloop()
