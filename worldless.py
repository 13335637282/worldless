import tkinter as tk
from tkinter import messagebox, ttk, simpledialog
import urllib.request
import base64
import os
import random
import re
import csv
import threading
import time
import queue


class WordleGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Wordle 单词游戏")
        self.root.geometry("500x700")
        self.root.configure(bg="#121213")

        # 常量
        self.DICT_URL = "https://gitee.com/yuxiqin/100000-english-words/raw/master/EnWords.csv"
        self.LOCAL_DICT = "EnWords.csv"
        self.SEPARATOR = "::"

        # 游戏状态
        self.dictionary = []
        self.word_meanings = {}
        self.target_word = ""
        self.word_length = 5
        self.max_attempts = 6
        self.current_attempt = 0
        self.dictionary_loaded = False  # 标记词库是否已加载

        # 颜色定义
        self.CORRECT_COLOR = "#6AAA64"  # 绿色
        self.PRESENT_COLOR = "#C9B458"  # 黄色
        self.ABSENT_COLOR = "#787C7E"  # 灰色
        self.DEFAULT_BG = "#121213"  # 背景色
        self.DEFAULT_BORDER = "#3A3A3C"  # 边框色
        self.KEY_DEFAULT = "#818384"  # 键盘默认颜色
        self.TEXT_COLOR = "#D7DADC"  # 文字颜色

        # 创建UI
        self.create_menu()
        self.create_game_grid()
        self.create_status_bar()
        self.create_keyboard()

        # 用于线程通信的队列
        self.message_queue = queue.Queue()

        # 加载词库
        self.load_dictionary()

        # 绑定键盘事件
        self.root.bind("<Key>", self.handle_key_press)

        # 定期检查消息队列
        self.root.after(100, self.process_queue)

    def process_queue(self):
        """处理线程发送到主线程的消息"""
        try:
            while True:
                msg = self.message_queue.get_nowait()
                if msg == "CLOSE_LOADING":
                    if hasattr(self, 'loading_window') and self.loading_window.winfo_exists():
                        self.loading_window.destroy()
                elif msg == "START_GAME":
                    self.start_new_game()
                elif msg.startswith("ERROR:"):
                    messagebox.showerror("错误", msg[6:])
                    self.root.destroy()
                elif msg.startswith("STATUS:"):
                    self.status_var.set(msg[7:])
                elif msg == "DICT_LOADED":
                    self.dictionary_loaded = True
                    self.status_var.set(f"词库加载完成: {len(self.dictionary)} 个单词")
                    self.root.after(100, self.start_new_game)
        except queue.Empty:
            pass
        self.root.after(100, self.process_queue)

    def create_menu(self):
        # 创建菜单栏
        menu_bar = tk.Menu(self.root)
        self.root.config(menu=menu_bar)

        # 创建游戏菜单
        game_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="游戏", menu=game_menu)

        game_menu.add_command(label="新游戏", command=self.show_game_settings)
        game_menu.add_command(label="导入游戏", command=self.import_game)
        game_menu.add_command(label="导出游戏", command=self.export_game)

        # 创建帮助菜单
        help_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="帮助", menu=help_menu)
        help_menu.add_command(label="游戏规则", command=self.show_instructions)

    def create_game_grid(self):
        # 创建游戏网格框架
        self.game_frame = tk.Frame(self.root, bg=self.DEFAULT_BG)
        self.game_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        # 创建滚动区域
        self.canvas = tk.Canvas(self.game_frame, bg=self.DEFAULT_BG, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.game_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.DEFAULT_BG)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # 布局滚动区域
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 创建字母网格
        self.letter_grid = []
        self.create_letter_grid()

    def create_letter_grid(self):
        # 清除现有网格
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        self.letter_grid = []

        # 创建网格布局
        grid_frame = tk.Frame(self.scrollable_frame, bg=self.DEFAULT_BG)
        grid_frame.pack(padx=10, pady=10)

        for row in range(self.max_attempts):
            row_labels = []
            for col in range(self.word_length):
                label = tk.Label(
                    grid_frame,
                    text="",
                    font=("Microsoft YaHei", 32, "bold"),
                    width=2,
                    relief="solid",
                    borderwidth=2,
                    bg=self.DEFAULT_BG,
                    fg=self.TEXT_COLOR,
                    highlightbackground=self.DEFAULT_BORDER,
                    highlightcolor=self.DEFAULT_BORDER,
                    highlightthickness=2
                )
                label.grid(row=row, column=col, padx=5, pady=5)
                row_labels.append(label)
            self.letter_grid.append(row_labels)

    def create_status_bar(self):
        # 创建状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("正在加载词库...")

        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            font=("Microsoft YaHei", 12),
            bg=self.DEFAULT_BG,
            fg=self.TEXT_COLOR,
            pady=10,
            wraplength=480,
            justify="center"
        )
        self.status_bar.pack(fill=tk.X, padx=10)

    def create_keyboard(self):
        # 创建键盘框架
        self.keyboard_frame = tk.Frame(self.root, bg=self.DEFAULT_BG, padx=10, pady=10)
        self.keyboard_frame.pack(fill=tk.BOTH)

        # 键盘布局
        keyboard_rows = [
            "qwertyuiop",
            "asdfghjkl",
            "zxcvbnm"
        ]

        self.key_buttons = {}
        self.key_colors = {}

        for row_idx, row in enumerate(keyboard_rows):
            row_frame = tk.Frame(self.keyboard_frame, bg=self.DEFAULT_BG)
            row_frame.pack(fill=tk.X, pady=3)

            for char in row:
                btn = tk.Button(
                    row_frame,
                    text=char.upper(),
                    font=("Microsoft YaHei", 14, "bold"),
                    width=4,
                    bg=self.KEY_DEFAULT,
                    fg=self.TEXT_COLOR,
                    relief="raised",
                    borderwidth=0,
                    command=lambda c=char: self.add_letter(c)
                )
                btn.pack(side=tk.LEFT, padx=2)
                self.key_buttons[char] = btn
                self.key_colors[char] = self.KEY_DEFAULT

        # 控制按钮行
        control_frame = tk.Frame(self.keyboard_frame, bg=self.DEFAULT_BG)
        control_frame.pack(fill=tk.X, pady=3)

        backspace_btn = tk.Button(
            control_frame,
            text="←",
            font=("Microsoft YaHei", 14, "bold"),
            width=4,
            bg=self.KEY_DEFAULT,
            fg=self.TEXT_COLOR,
            relief="raised",
            borderwidth=0,
            command=self.remove_letter
        )
        backspace_btn.pack(side=tk.LEFT, padx=2)

        enter_btn = tk.Button(
            control_frame,
            text="确定",
            font=("Microsoft YaHei", 14, "bold"),
            width=10,
            bg=self.KEY_DEFAULT,
            fg=self.TEXT_COLOR,
            relief="raised",
            borderwidth=0,
            command=self.submit_guess
        )
        enter_btn.pack(side=tk.RIGHT, padx=2)

    def show_instructions(self):
        instructions = """
        Wordle 游戏规则：

        1. 游戏会随机选择一个英文单词作为目标词
        2. 你有有限次数的尝试机会来猜出这个单词
        3. 每次尝试后，字母的颜色会给出提示：
           - 绿色：字母在正确位置
           - 黄色：字母在单词中但位置错误
           - 灰色：字母不在单词中
        4. 使用这些提示来改进你的下一次猜测
        5. 在尝试次数用完前猜出单词即为胜利

        提示：
        - 可以从常见元音字母开始尝试
        - 注意字母的颜色提示来排除可能性
        - 尝试使用包含不同字母的单词
        """

        messagebox.showinfo("游戏规则", instructions)

    def load_dictionary(self):
        # 检查本地词库是否存在
        if not os.path.exists(self.LOCAL_DICT):
            # 显示加载窗口
            self.show_loading_window()
            # 在新线程中下载词库
            threading.Thread(target=self.download_dictionary_thread, daemon=True).start()
        else:
            # 直接加载词库
            threading.Thread(target=self.load_dictionary_from_file_thread, daemon=True).start()

    def show_loading_window(self):
        self.loading_window = tk.Toplevel(self.root)
        self.loading_window.title("加载词库")
        self.loading_window.geometry("300x200")
        self.loading_window.transient(self.root)
        self.loading_window.grab_set()
        self.loading_window.resizable(False, False)

        # 创建加载动画
        loading_label = tk.Label(
            self.loading_window,
            text="正在下载词库...",
            font=("Microsoft YaHei", 14),
            pady=20
        )
        loading_label.pack()

        # 创建进度条
        self.progress = ttk.Progressbar(
            self.loading_window,
            orient="horizontal",
            length=250,
            mode="indeterminate"
        )
        self.progress.pack(pady=10)
        self.progress.start(10)

        # 创建说明文本
        info_label = tk.Label(
            self.loading_window,
            text="首次运行需要下载词库\n请稍候...",
            font=("Microsoft YaHei", 10),
            pady=10,
            justify="center"
        )
        info_label.pack()

        # 创建取消按钮
        cancel_btn = tk.Button(
            self.loading_window,
            text="取消",
            command=self.cancel_download,
            width=10
        )
        cancel_btn.pack(pady=10)

        # 更新窗口
        self.loading_window.update()

    def cancel_download(self):
        if hasattr(self, 'loading_window') and self.loading_window:
            self.loading_window.destroy()
        self.root.destroy()

    def download_dictionary_thread(self):
        try:
            # 发送状态消息到主线程
            self.message_queue.put("STATUS:正在下载词库...")

            # 实际下载词库
            with urllib.request.urlopen(self.DICT_URL) as response:
                data = response.read().decode("utf-8")

            # 保存到文件
            with open(self.LOCAL_DICT, "w", encoding="utf-8") as file:
                file.write(data)

            # 发送消息关闭加载窗口
            self.message_queue.put("CLOSE_LOADING")

            # 加载词库
            self.load_dictionary_from_file_thread()

        except Exception as e:
            self.message_queue.put(f"ERROR:下载词库失败: {str(e)}")

    def load_dictionary_from_file_thread(self):
        try:
            # 发送状态消息到主线程
            self.message_queue.put("STATUS:正在加载词库...")

            with open(self.LOCAL_DICT, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                for row in reader:
                    if len(row) < 2:
                        continue

                    word = row[0].strip().lower()
                    meaning = row[1].strip()

                    # 只保留3-12字母的单词
                    if 3 <= len(word) <= 12 and re.match(r"^[a-z]+$", word):
                        self.dictionary.append(word)
                        self.word_meanings[word] = meaning

            # 标记词库已加载
            self.message_queue.put("DICT_LOADED")

        except Exception as e:
            self.message_queue.put(f"ERROR:加载词库失败: {str(e)}")

    def start_new_game(self):
        # 确保词库已加载
        if not self.dictionary_loaded:
            self.status_var.set("词库尚未加载完成，请稍候...")
            return

        # 过滤指定长度的单词
        filtered = [word for word in self.dictionary if len(word) == self.word_length]

        if not filtered:
            messagebox.showerror("错误", f"没有找到长度为 {self.word_length} 的单词")
            return

        # 随机选择目标单词
        self.target_word = random.choice(filtered)
        self.current_attempt = 0
        self.reset_ui()
        self.status_var.set(f"新游戏开始! 单词长度: {self.word_length}, 尝试次数: {self.max_attempts}")

    def reset_ui(self):
        # 重置游戏网格
        self.create_letter_grid()

        # 重置键盘颜色
        for char, btn in self.key_buttons.items():
            btn.configure(bg=self.KEY_DEFAULT)
            self.key_colors[char] = self.KEY_DEFAULT

        # 重置滚动区域
        self.canvas.yview_moveto(0.0)

    def add_letter(self, char):
        if not self.dictionary_loaded:
            self.status_var.set("词库尚未加载完成，请稍候...")
            return

        if self.current_attempt >= self.max_attempts:
            return

        # 找到当前行第一个空位置
        for col in range(self.word_length):
            if not self.letter_grid[self.current_attempt][col].cget("text"):
                self.letter_grid[self.current_attempt][col].configure(text=char.upper())
                return

    def remove_letter(self):
        if not self.dictionary_loaded:
            return

        if self.current_attempt >= self.max_attempts:
            return

        # 从当前行最后一个字母开始删除
        for col in range(self.word_length - 1, -1, -1):
            if self.letter_grid[self.current_attempt][col].cget("text"):
                self.letter_grid[self.current_attempt][col].configure(text="")
                return

    def submit_guess(self):
        if not self.dictionary_loaded:
            self.status_var.set("词库尚未加载完成，请稍候...")
            return

        if self.current_attempt >= self.max_attempts:
            return

        # 收集当前行的字母
        guess_chars = []
        for col in range(self.word_length):
            letter = self.letter_grid[self.current_attempt][col].cget("text")
            if not letter:
                self.status_var.set("请完成单词输入！")
                return
            guess_chars.append(letter.lower())

        guess = "".join(guess_chars)

        # 检查单词是否在词库中
        if guess not in self.dictionary:
            self.status_var.set("单词不在词库中！")
            return

        # 处理猜测
        self.process_guess(guess)
        self.current_attempt += 1

        # 更新状态栏
        meaning = self.word_meanings.get(guess, "")
        if meaning:
            self.status_var.set(f"已提交: {guess.upper()}\n{meaning}")
        else:
            self.status_var.set(f"已提交: {guess.upper()}")

        # 检查游戏结果
        if guess == self.target_word:
            self.game_won()
        elif self.current_attempt == self.max_attempts:
            self.game_lost()

        # 如果尝试次数多，滚动到最新一行
        if self.max_attempts > 10:
            self.scroll_to_current_row()

    def scroll_to_current_row(self):
        # 计算当前行在画布中的位置
        row_height = 60  # 每行的估计高度
        scroll_position = min(1.0, (self.current_attempt * row_height) / (self.max_attempts * row_height))
        self.canvas.yview_moveto(scroll_position)

    def process_guess(self, guess):
        # 复制目标词字母计数
        target_count = {}
        for char in self.target_word:
            target_count[char] = target_count.get(char, 0) + 1

        # 先标记正确位置（绿色）
        for i in range(len(guess)):
            guess_char = guess[i]
            if guess_char == self.target_word[i]:
                self.letter_grid[self.current_attempt][i].configure(
                    bg=self.CORRECT_COLOR,
                    fg="white"
                )
                target_count[guess_char] -= 1

        # 再标记其他情况
        for i in range(len(guess)):
            guess_char = guess[i]
            label = self.letter_grid[self.current_attempt][i]

            # 如果已经是绿色，跳过
            if label.cget("bg") == self.CORRECT_COLOR:
                continue

            # 如果字母在目标词中且还有剩余，标记为黄色
            if guess_char in self.target_word and target_count.get(guess_char, 0) > 0:
                label.configure(
                    bg=self.PRESENT_COLOR,
                    fg="white"
                )
                target_count[guess_char] -= 1
            else:
                label.configure(
                    bg=self.ABSENT_COLOR,
                    fg="white"
                )

        # 更新键盘颜色
        for char in guess:
            # 获取当前字母在键盘上的按钮
            btn = self.key_buttons.get(char)
            if not btn:
                continue

            # 获取当前字母在网格中的颜色
            char_color = None
            for i in range(len(guess)):
                if guess[i] == char:
                    label_color = self.letter_grid[self.current_attempt][i].cget("bg")
                    if label_color == self.CORRECT_COLOR:
                        char_color = self.CORRECT_COLOR
                    elif label_color == self.PRESENT_COLOR and char_color != self.CORRECT_COLOR:
                        char_color = self.PRESENT_COLOR
                    elif label_color == self.ABSENT_COLOR and char_color != self.CORRECT_COLOR and char_color != self.PRESENT_COLOR:
                        char_color = self.ABSENT_COLOR

            # 更新键盘按钮颜色
            if char_color and char_color != self.key_colors[char]:
                btn.configure(bg=char_color, fg="white")
                self.key_colors[char] = char_color

    def game_won(self):
        meaning = self.word_meanings.get(self.target_word, "")
        if meaning:
            self.status_var.set(f"恭喜你猜对了！单词: {self.target_word.upper()}\n{meaning}")
        else:
            self.status_var.set(f"恭喜你猜对了！单词: {self.target_word.upper()}")

        # 禁用输入
        self.root.unbind("<Key>")

        # 显示胜利动画
        self.show_victory_animation()

    def show_victory_animation(self):
        # 在胜利时添加一些视觉效果
        for row in range(self.max_attempts):
            for col in range(self.word_length):
                if row < self.current_attempt:
                    self.animate_label(self.letter_grid[row][col])

    def animate_label(self, label):
        # 简单的动画效果
        original_bg = label.cget("bg")

        def flash():
            current_bg = label.cget("bg")
            if current_bg == original_bg:
                label.configure(bg="#FFFFFF")
                label.after(100, flash)
            else:
                label.configure(bg=original_bg)

        flash()

    def game_lost(self):
        meaning = self.word_meanings.get(self.target_word, "")
        if meaning:
            self.status_var.set(f"游戏结束！正确答案: {self.target_word.upper()}\n{meaning}")
        else:
            self.status_var.set(f"游戏结束！正确答案: {self.target_word.upper()}")

        # 禁用输入
        self.root.unbind("<Key>")

        # 高亮显示正确答案
        self.highlight_solution()

    def highlight_solution(self):
        # 高亮显示正确答案
        for row in range(self.max_attempts):
            for col in range(self.word_length):
                if row == self.current_attempt - 1:
                    self.letter_grid[row][col].configure(
                        bg="#FF6B6B",  # 浅红色
                        fg="white"
                    )

    def show_game_settings(self):
        if not self.dictionary_loaded:
            messagebox.showinfo("提示", "词库尚未加载完成，请稍候再试")
            return

        # 创建设置对话框
        settings_dialog = tk.Toplevel(self.root)
        settings_dialog.title("新游戏设置")
        settings_dialog.geometry("300x150")
        settings_dialog.transient(self.root)
        settings_dialog.grab_set()
        settings_dialog.resizable(False, False)

        # 单词长度设置
        tk.Label(settings_dialog, text="单词长度 (3-12):", font=("Microsoft YaHei", 10)).grid(row=0, column=0, padx=5,
                                                                                              pady=5, sticky="e")
        length_spin = tk.Spinbox(settings_dialog, from_=3, to=12, width=5, font=("Microsoft YaHei", 10))
        length_spin.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        length_spin.delete(0, tk.END)
        length_spin.insert(0, str(self.word_length))

        # 尝试次数设置
        tk.Label(settings_dialog, text="尝试次数 (1-200):", font=("Microsoft YaHei", 10)).grid(row=1, column=0, padx=5,
                                                                                               pady=5, sticky="e")
        attempts_spin = tk.Spinbox(settings_dialog, from_=1, to=200, width=5, font=("Microsoft YaHei", 10))
        attempts_spin.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        attempts_spin.delete(0, tk.END)
        attempts_spin.insert(0, str(self.max_attempts))

        # 按钮
        def apply_settings():
            try:
                new_length = int(length_spin.get())
                new_attempts = int(attempts_spin.get())

                if 3 <= new_length <= 12 and 1 <= new_attempts <= 200:
                    self.word_length = new_length
                    self.max_attempts = new_attempts
                    settings_dialog.destroy()
                    self.start_new_game()
                    self.root.bind("<Key>", self.handle_key_press)
                else:
                    messagebox.showerror("错误", "请输入有效的设置值")
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")

        tk.Button(
            settings_dialog,
            text="确定",
            command=apply_settings,
            font=("Microsoft YaHei", 10),
            width=10
        ).grid(row=2, column=0, columnspan=2, pady=10)

    def import_game(self):
        if not self.dictionary_loaded:
            messagebox.showinfo("提示", "词库尚未加载完成，请稍候再试")
            return

        input_str = simpledialog.askstring("导入游戏", "请输入游戏代码:")
        if not input_str:
            return

        try:
            # 解码游戏代码
            decoded = base64.b64decode(input_str).decode("utf-8")
            parts = decoded.split(self.SEPARATOR)

            if len(parts) != 2:
                raise ValueError("无效的游戏代码格式")

            word = parts[0].strip().lower()
            chances = int(parts[1].strip())

            # 验证输入
            if word not in self.dictionary:
                raise ValueError("单词不在词库中")

            if not (3 <= len(word) <= 12):
                raise ValueError("单词长度必须在3-12之间")

            if not (1 <= chances <= 200):
                raise ValueError("尝试次数必须在1-200之间")

            # 更新游戏状态
            self.target_word = word
            self.word_length = len(word)
            self.max_attempts = chances
            self.current_attempt = 0

            # 重置UI并开始新游戏
            self.reset_ui()
            self.status_var.set(f"游戏已导入: {self.word_length} 个字母, {self.max_attempts} 次尝试机会")
            self.root.bind("<Key>", self.handle_key_press)

        except Exception as e:
            messagebox.showerror("错误", f"导入游戏失败: {str(e)}")

    def export_game(self):
        if not self.dictionary_loaded:
            messagebox.showinfo("提示", "词库尚未加载完成，请稍候再试")
            return

        # 创建导出对话框
        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("导出游戏")
        export_dialog.geometry("400x250")
        export_dialog.transient(self.root)
        export_dialog.grab_set()
        export_dialog.resizable(False, False)

        # 单词输入
        tk.Label(export_dialog, text="最终答案(必须为单词):", font=("Microsoft YaHei", 10)).grid(row=0, column=0,
                                                                                                 padx=5, pady=5,
                                                                                                 sticky="e")
        word_entry = tk.Entry(export_dialog, width=20, font=("Microsoft YaHei", 10))
        word_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # 尝试次数输入
        tk.Label(export_dialog, text="最多尝试次数 (1~200):", font=("Microsoft YaHei", 10)).grid(row=1, column=0,
                                                                                                 padx=5, pady=5,
                                                                                                 sticky="e")
        attempts_spin = tk.Spinbox(export_dialog, from_=1, to=200, width=5, font=("Microsoft YaHei", 10))
        attempts_spin.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        attempts_spin.delete(0, tk.END)
        attempts_spin.insert(0, "6")

        # 生成代码
        tk.Label(export_dialog, text="生成代码:", font=("Microsoft YaHei", 10)).grid(row=2, column=0, padx=5, pady=5,
                                                                                     sticky="e")
        code_var = tk.StringVar()
        code_entry = tk.Entry(export_dialog, textvariable=code_var, state="readonly", width=30,
                              font=("Microsoft YaHei", 10))
        code_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # 按钮框架
        button_frame = tk.Frame(export_dialog)
        button_frame.grid(row=3, column=0, columnspan=2, pady=10)

        def generate_code():
            word = word_entry.get().strip().lower()

            # 验证输入
            if not word:
                messagebox.showerror("错误", "请输入单词")
                return

            if not (3 <= len(word) <= 12):
                messagebox.showerror("错误", "单词长度必须在3-12之间")
                return

            if not re.match(r"^[a-z]+$", word):
                messagebox.showerror("错误", "单词只能包含字母")
                return

            if word not in self.dictionary:
                messagebox.showerror("错误", "单词不在词库中")
                return

            try:
                attempts = int(attempts_spin.get())
                if not (1 <= attempts <= 200):
                    raise ValueError
            except ValueError:
                messagebox.showerror("错误", "请输入有效的尝试次数")
                return

            # 生成游戏代码
            game_data = f"{word}{self.SEPARATOR}{attempts}"
            code = base64.b64encode(game_data.encode("utf-8")).decode("utf-8")
            code_var.set(code)

        def copy_code():
            code = code_var.get()
            if not code:
                messagebox.showinfo("提示", "请先生成代码")
                return

            export_dialog.clipboard_clear()
            export_dialog.clipboard_append(code)
            messagebox.showinfo("成功", "代码已复制到剪贴板")

        tk.Button(
            button_frame,
            text="生成",
            command=generate_code,
            font=("Microsoft YaHei", 10),
            width=8
        ).pack(side=tk.LEFT, padx=5)

        tk.Button(
            button_frame,
            text="复制代码",
            command=copy_code,
            font=("Microsoft YaHei", 10),
            width=8
        ).pack(side=tk.LEFT, padx=5)

    def handle_key_press(self, event):
        # 处理键盘事件
        char = event.char.lower()

        if event.keysym == "BackSpace":
            self.remove_letter()
        elif event.keysym == "Return":
            self.submit_guess()
        elif "a" <= char <= "z":
            self.add_letter(char)


def main():
    root = tk.Tk()
    # 设置应用程序图标
    try:
        # 创建一个简单的字母W图标
        from PIL import Image, ImageDraw
        img = Image.new('RGB', (64, 64), color=(106, 170, 100))
        d = ImageDraw.Draw(img)
        d.text((20, 20), "W", fill=(255, 255, 255))
        icon = tk.PhotoImage(data=img.tobytes())
        root.iconphoto(True, icon)
    except:
        pass

    game = WordleGame(root)
    root.mainloop()


if __name__ == "__main__":
    main()