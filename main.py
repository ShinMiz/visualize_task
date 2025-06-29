import tkinter as tk
from tkinter import messagebox, simpledialog
import time
import sqlite3
import datetime
import json
import colorsys
from tkcalendar import DateEntry


class TaskApp:
    def __init__(self, master):
        self.master = master
        master.title("タスク管理アプリ")
        master.geometry("500x600")

        self.db_path = "tasks.db"
        self.conn = sqlite3.connect(self.db_path)
        self._create_table()

        self.categories = self._load_categories()
        self._generate_category_colors()

        self.tasks = self._load_tasks_from_db()
        self.task_rects = {}

        self._build_ui(master)
        self.update_time()
        self.render_tasks()
        self.blinking_rects = {}
        self.blink_state = True
        self.blink_overdue_rects()
        self.output_window = None  # 初期化（あとで開く）
        self.open_output_window()

    def _build_ui(self, master):
        self.time_label = tk.Label(master, text="", anchor="e")
        self.time_label.place(relx=1.0, anchor="ne", x=-10, y=10)

        tk.Label(master, text="タスク名（必須）").pack()
        self.task_entry = tk.Entry(master, width=50)
        self.task_entry.pack()

        tk.Label(master, text="詳細").pack()
        self.detail_entry = tk.Entry(master, width=50)
        self.detail_entry.pack()

        tk.Label(master, text="カテゴリー").pack()
        self.category_var = tk.StringVar(master)
        self.category_var.set(self.categories[0])
        self.category_menu = tk.OptionMenu(master, self.category_var, *self.categories)
        self.category_menu.pack()

        tk.Button(master, text="カテゴリ管理", command=self._open_category_manager).pack()

        tk.Label(master, text="期限日").pack()
        self.date_entry = DateEntry(master, width=20, date_pattern='yyyy-mm-dd')
        self.date_entry.pack()
        self.no_due_var = tk.BooleanVar()
        self.no_due_check = tk.Checkbutton(master, text="期限を定めない", variable=self.no_due_var)
        self.no_due_check.pack()

        time_frame = tk.Frame(master)
        time_frame.pack()
        tk.Label(time_frame, text="時").pack(side="left")
        self.hour_var = tk.StringVar()
        self.hour_var.set("12")
        tk.OptionMenu(time_frame, self.hour_var, *[f"{i:02d}" for i in range(24)]).pack(side="left")
        tk.Label(time_frame, text="分").pack(side="left")
        self.minute_var = tk.StringVar()
        self.minute_var.set("00")
        tk.OptionMenu(time_frame, self.minute_var, *[f"{i:02d}" for i in range(60)]).pack(side="left")

        tk.Label(master, text="重要度（1以上の整数）").pack()
        self.importance_entry = tk.Entry(master, width=20)
        self.importance_entry.pack()

        self.add_button = tk.Button(master, text="タスクを追加", command=self.add_task)
        self.add_button.pack(pady=5)

        self.canvas = tk.Canvas(master, bg="white", width=480, height=300)
        self.canvas.pack(pady=10)
        self.reset_button = tk.Button(master, text="全てリセット（ダブルクリック）")
        self.reset_button.pack(pady=5)
        self.reset_button.bind("<Double-Button-1>", self._confirm_reset)
        self.show_output_button = tk.Button(master, text="可視化画面を開く", command=self.open_output_window)
        self.show_output_button.pack(pady=5)


    def _load_categories(self, path="categories.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                categories = json.load(f)
                if not categories:
                    raise ValueError
                return categories
        except:
            return ["医学"]

    def _save_categories(self, path="categories.json"):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.categories, f, ensure_ascii=False)

    def _generate_category_colors(self):
        n = len(self.categories)
        self.category_colors = {}
        for i, cat in enumerate(self.categories):
            h = i / max(n, 1)
            r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(h, 0.6, 1.0)]
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            self.category_colors[cat] = hex_color
    def open_output_window(self):
        if self.output_window is None or not self.output_window.winfo_exists():
            self.output_window = OutputWindow(self.master, self)
        else:
            self.output_window.lift()  # すでに開いていれば前面に

    def _create_table(self):
        c = self.conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                detail TEXT,
                category TEXT,
                due_date TEXT,
                importance INTEGER,
                created_at TEXT
            )
        ''')
        self.conn.commit()

    def _load_tasks_from_db(self):
        c = self.conn.cursor()
        c.execute("SELECT name, detail, category, due_date, importance, created_at FROM tasks")
        rows = c.fetchall()
        return [{"name": r[0], "detail": r[1], "category": r[2], "due": r[3], "importance": r[4], "created_at": r[5]} for r in rows]

    def update_time(self):
        self.time_label.config(text=time.strftime("%H:%M:%S"))
        self.master.after(1000, self.update_time)
        self.render_tasks()

    def add_task(self):
        name = self.task_entry.get().strip()
        detail = self.detail_entry.get().strip()
        category = self.category_var.get()
        if self.no_due_var.get():
            due = "none"
        else:
            due = f"{self.date_entry.get()} {self.hour_var.get()}:{self.minute_var.get()}:00"

        importance = self.importance_entry.get().strip()

        if not name:
            messagebox.showwarning("入力エラー", "タスク名は必須です。")
            return

        try:
            importance = int(importance)
            if importance <= 0:
                raise ValueError
        except:
            messagebox.showwarning("入力エラー", "重要度は1以上の整数で入力してください。")
            return

        created_at = datetime.datetime.now().isoformat()

        c = self.conn.cursor()
        c.execute("INSERT INTO tasks (name, detail, category, due_date, importance, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                  (name, detail, category, due, importance, created_at))
        self.conn.commit()

        self.tasks.append({"name": name, "detail": detail, "category": category, "due": due,
                           "importance": importance, "created_at": created_at})

        self._clear_inputs()
        self.render_tasks()
        if self.output_window:
            self.output_window.render_tasks()


    def _clear_inputs(self):
        self.task_entry.delete(0, tk.END)
        self.detail_entry.delete(0, tk.END)
        self.importance_entry.delete(0, tk.END)

    def render_tasks(self):
        self.canvas.delete("all")
        self.task_rects.clear()
        if not self.tasks:
            return

        tasks = sorted(
            self.tasks,
            key=lambda t: self.categories.index(t["category"]) if t["category"] in self.categories else len(self.categories)
        )
        total = sum(t["importance"] for t in tasks)
        if total == 0:
            return

        width, height = 480, 300
        x, y = 0, 0
        row_height = 0

        for task in tasks:
            area_ratio = task["importance"] / total
            area = width * height * area_ratio
            w = max(int(area ** 0.5), 1)
            h = max(int(area / w), 1)
            if x + w > width:
                x = 0
                y += row_height
                row_height = 0
            base_color = self.category_colors.get(task["category"], "#cccccc")
            fill_color = self._get_faded_color(base_color, task["created_at"], task["due"])
            rect_id = self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill_color, outline=base_color, width=4)
            self.canvas.create_text(x + 4, y + 4, anchor="nw", text=task["name"], font=("Arial", 8, "bold"))
            self.canvas.create_text(x + 4, y + 20, anchor="nw", text=task["detail"], font=("Arial", 7), fill="gray20")
            self.task_rects[rect_id] = task
            self.canvas.tag_bind(rect_id, "<Double-Button-1>", self._on_left_double_click)
            self.canvas.tag_bind(rect_id, "<Double-Button-3>", self._on_right_double_click)
            x += w
            row_height = max(row_height, h)
            try:
                due_dt = datetime.datetime.fromisoformat(task["due"])
                if due_dt < datetime.datetime.now():
                    self.blinking_rects[rect_id] = True
            except:
                pass
        if task["due"] != "none":
            self.canvas.create_text(x + 4, y + 36, anchor="nw", 
                text=f"期限: {task['due']}", font=("Arial", 7), fill="gray40")

            
    def blink_overdue_rects(self):
        for rect_id in list(self.blinking_rects.keys()):
            try:
                self.canvas.itemconfig(
                    rect_id,
                    fill="#ff0000" if self.blink_state else ""
                )
            except tk.TclError:
                del self.blinking_rects[rect_id]
        self.blink_state = not self.blink_state
        self.master.after(500, self.blink_overdue_rects)

    def _get_faded_color(self, base_hex, created_at_str, due_str):
        if due_str == "none":
            # 期限なしの中間色（固定色）
            return base_hex

        try:
            created_at = datetime.datetime.fromisoformat(created_at_str)
            due = datetime.datetime.fromisoformat(due_str)
            now = datetime.datetime.now()
            total = (due - created_at).total_seconds()
            elapsed = (now - created_at).total_seconds()
            ratio = min(max(elapsed / total, 0), 1)
        except:
            ratio = 0

        fade_start_ratio = 0.2  # ← 0.0 なら完全白、0.2なら「やや白寄り」から始まる
        adjusted_ratio = fade_start_ratio + (1 - fade_start_ratio) * ratio

        r, g, b = self._hex_to_rgb(base_hex)
        r = int(255 - (255 - r) * adjusted_ratio)
        g = int(255 - (255 - g) * adjusted_ratio)
        b = int(255 - (255 - b) * adjusted_ratio)
        return f"#{r:02x}{g:02x}{b:02x}"


    def _hex_to_rgb(self, hex_code):
        hex_code = hex_code.lstrip('#')
        return tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))

    def _on_left_double_click(self, event):
        canvas_id = event.widget.find_closest(event.x, event.y)[0]
        task = self.task_rects.get(canvas_id)
        if task and messagebox.askyesno("削除確認", f"{task['name']} を削除してもよいですか？"):
            self._delete_task(task)

    def _delete_task(self, task):
        c = self.conn.cursor()
        c.execute("DELETE FROM tasks WHERE name=? AND created_at=?", (task["name"], task["created_at"]))
        self.conn.commit()
        self.tasks.remove(task)
        self.render_tasks()
        if self.output_window:
           self.output_window.render_tasks()


    def _on_right_double_click(self, event):
        canvas_id = event.widget.find_closest(event.x, event.y)[0]
        task = self.task_rects.get(canvas_id)
        if task:
            self._open_edit_dialog(task)

    def _open_edit_dialog(self, task):
        win = tk.Toplevel(self.master)
        win.title("タスク編集")

        name_entry = tk.Entry(win, width=40)
        name_entry.insert(0, task["name"])
        name_entry.pack()

        detail_entry = tk.Entry(win, width=40)
        detail_entry.insert(0, task["detail"])
        detail_entry.pack()

        due_str = task.get("due", "")
        if due_str == "none":
            date = datetime.datetime.now().strftime("%Y-%m-%d")
            hour = "12"
            minute = "00"
        else:
            try:
                date_part, time_part = due_str.split(" ")
                date = date_part
                hour, minute = time_part[:5].split(":")
            except Exception:
                date = datetime.datetime.now().strftime("%Y-%m-%d")
                hour = "12"
                minute = "00"

        date_entry = DateEntry(win, width=20, date_pattern='yyyy-mm-dd')
        date_entry.set_date(date)
        date_entry.pack()

        time_frame = tk.Frame(win)
        time_frame.pack()
        hour_var = tk.StringVar()
        hour_var.set(hour)
        tk.Label(time_frame, text="時").pack(side="left")
        tk.OptionMenu(time_frame, hour_var, *[f"{i:02d}" for i in range(24)]).pack(side="left")
        minute_var = tk.StringVar()
        minute_var.set(minute)
        tk.Label(time_frame, text="分").pack(side="left")
        tk.OptionMenu(time_frame, minute_var, *[f"{i:02d}" for i in range(60)]).pack(side="left")

        importance_entry = tk.Entry(win, width=10)
        importance_entry.insert(0, str(task["importance"]))
        importance_entry.pack()

        def save():
            try:
                new_importance = int(importance_entry.get())
            except:
                messagebox.showerror("エラー", "重要度は整数で入力してください")
                return
            new_due = f"{date_entry.get()} {hour_var.get()}:{minute_var.get()}:00"
            c = self.conn.cursor()
            c.execute("""
                UPDATE tasks SET name=?, detail=?, due_date=?, importance=?
                WHERE name=? AND created_at=?
            """, (name_entry.get(), detail_entry.get(), new_due, new_importance,
                task["name"], task["created_at"]))
            self.conn.commit()
            task["name"] = name_entry.get()
            task["detail"] = detail_entry.get()
            task["due"] = new_due
            task["importance"] = new_importance
            win.destroy()
            self.render_tasks()

        tk.Button(win, text="保存", command=save).pack(pady=5)


    def _open_category_manager(self):
        win = tk.Toplevel(self.master)
        win.title("カテゴリ管理")
        listbox = tk.Listbox(win)
        for c in self.categories:
            listbox.insert(tk.END, c)
        listbox.pack()

        def add():
            new = simpledialog.askstring("カテゴリ追加", "新しいカテゴリ名：", parent=win)
            if new and new not in self.categories:
                self.categories.append(new)
                self._save_categories()
                self._generate_category_colors()
                listbox.insert(tk.END, new)
                self._refresh_category_menu()
                self.render_tasks()

        def delete():
            sel = listbox.curselection()
            if sel:
                cat = self.categories[sel[0]]
                if messagebox.askyesno("削除確認", f"{cat} を削除しますか？"):
                    del self.categories[sel[0]]
                    self._save_categories()
                    self._generate_category_colors()
                    listbox.delete(sel[0])
                    self._refresh_category_menu()
                    self.render_tasks()

        tk.Button(win, text="追加", command=add).pack(side="left")
        tk.Button(win, text="削除", command=delete).pack(side="left")

    def _refresh_category_menu(self):
        menu = self.category_menu['menu']
        menu.delete(0, 'end')
        for c in self.categories:
            menu.add_command(label=c, command=lambda v=c: self.category_var.set(v))
    def _confirm_reset(self, event):
        if messagebox.askyesno("全削除の確認", "本当に全てのタスクを削除しますか？この操作は元に戻せません。"):
            self._reset_all_tasks()

    def _reset_all_tasks(self):
        c = self.conn.cursor()
        c.execute("DELETE FROM tasks")
        self.conn.commit()
        self.tasks.clear()
        self.render_tasks()
        self.blinking_rects.clear()


class OutputWindow(tk.Toplevel):
    def __init__(self, master, task_app):
        super().__init__(master)
        self.title("タスク可視化")
        self.attributes('-fullscreen', True)
        self.configure(bg="#1e1e2f")  # ✅ ウィンドウ全体の背景色

        self.task_app = task_app
        self.canvas = tk.Canvas(self, bg="#1e1e2f", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.task_rects = {}
        self.blinking_rects = {}
        self.blink_state = True
        self.bind("<Escape>", lambda e: self.attributes("-fullscreen", False))
        self.font_title = ("Times New Roman", 12, "bold")      # ✅ タイトル用フォント
        self.font_detail = ("Times New Roman", 10, "normal")   # ✅ 詳細用フォント
        self.text_color = "#f0f0f0"                             # ✅ 明るい文字色

        self.render_tasks()
        self.blink_overdue_rects()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.canvas.bind("<Button-3>", self._on_right_click)


    def render_tasks(self):
        self.canvas.delete("all")
        self.task_rects.clear()
        tasks = self.task_app.tasks
        categories = self.task_app.categories
        category_colors = self.task_app.category_colors

        if not tasks:
            return

        tasks = sorted(tasks, key=lambda t: categories.index(t["category"]) if t["category"] in categories else len(categories))
        total = sum(t["importance"] for t in tasks)
        if total == 0:
            return

        width, height = 480, 300
        x, y, row_height = 0, 0, 0

        for task in tasks:
            area_ratio = task["importance"] / total
            area = width * height * area_ratio
            w = max(int(area ** 0.5), 1)
            h = max(int(area / w), 1)
            if x + w > width:
                x = 0
                y += row_height
                row_height = 0
            base_color = category_colors.get(task["category"], "#cccccc")
            fill_color = self.task_app._get_faded_color(base_color, task["created_at"], task["due"])
            rect_id = self.canvas.create_rectangle(x, y, x + w, y + h, fill=fill_color, outline=base_color, width=4)
            self.canvas.create_text(x + 4, y + 4, anchor="nw", text=task["name"],
                        font=self.font_title, fill=self.text_color)
            self.canvas.create_text(x + 4, y + 24, anchor="nw", text=task["detail"],
                                    font=self.font_detail, fill=self.text_color)

            self.task_rects[rect_id] = task
            self.canvas.tag_bind(rect_id, "<Double-Button-1>", self._on_left_double_click)
            self.canvas.tag_bind(rect_id, "<Double-Button-3>", self._on_right_double_click)
            x += w
            row_height = max(row_height, h)
            try:
                due_dt = datetime.datetime.fromisoformat(task["due"])
                if due_dt < datetime.datetime.now():
                    self.blinking_rects[rect_id] = True
            except:
                pass
        if task["due"] != "none":
            self.canvas.create_text(x + 4, y + 42, anchor="nw",
                text=f"期限: {task['due']}", font=("Times New Roman", 9), fill="#cccccc")


    def blink_overdue_rects(self):
        for rect_id in list(self.blinking_rects.keys()):
            try:
                self.canvas.itemconfig(
                    rect_id,
                    fill="#ff0000" if self.blink_state else ""
                )
            except tk.TclError:
                del self.blinking_rects[rect_id]
        self.blink_state = not self.blink_state
        self.after(500, self.blink_overdue_rects)

    def _on_left_double_click(self, event):
        canvas_id = event.widget.find_closest(event.x, event.y)[0]
        task = self.task_rects.get(canvas_id)
        if task and messagebox.askyesno("削除確認", f"{task['name']} を削除しますか？"):
            self.task_app._delete_task(task)
            self.render_tasks()

    def _on_right_double_click(self, event):
        canvas_id = event.widget.find_closest(event.x, event.y)[0]
        task = self.task_rects.get(canvas_id)
        if task:
            self.task_app._open_edit_dialog(task)
            self.render_tasks()
    def _on_right_click(self, event):
        canvas_id = event.widget.find_closest(event.x, event.y)[0]
        task = self.task_rects.get(canvas_id)
        if not task:
            return

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="状態をリセット", command=lambda: self._reset_task_timing(task))
        menu.add_command(label="新しい期限を選択", command=lambda: self._choose_new_due(task))
        menu.tk_popup(event.x_root, event.y_root)

    def _on_close(self):
        self.task_app.output_window = None
        self.destroy()
    def _reset_task_timing(self, task):
        now = datetime.datetime.now().isoformat()
        task["created_at"] = now
        task["due"] = (datetime.datetime.now() + datetime.timedelta(days=1)).isoformat()  # 仮の1日後
        c = self.task_app.conn.cursor()
        c.execute("UPDATE tasks SET created_at=?, due_date=? WHERE name=? AND created_at=?",
                (now, task["due"], task["name"], task["created_at"]))
        self.task_app.conn.commit()
        self.task_app.render_tasks()
        self.render_tasks()

    def _choose_new_due(self, task):
        def on_date_selected():
            date_str = date_picker.get_date().strftime("%Y-%m-%d")
            new_due = f"{date_str} 12:00:00"
            task["due"] = new_due
            c = self.task_app.conn.cursor()
            c.execute("UPDATE tasks SET due_date=? WHERE name=? AND created_at=?",
                    (new_due, task["name"], task["created_at"]))
            self.task_app.conn.commit()
            top.destroy()
            self.task_app.render_tasks()
            self.render_tasks()

        top = tk.Toplevel(self)
        top.title("期限を選択")
        date_picker = DateEntry(top, width=20, date_pattern='yyyy-mm-dd')
        date_picker.pack(pady=10)
        tk.Button(top, text="設定", command=on_date_selected).pack(pady=5)



if __name__ == "__main__":
    root = tk.Tk()
    app = TaskApp(root)
    root.mainloop()


