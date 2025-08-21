"""Simple Tkinter UI for adding stories to the database."""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox

from app.services.story_manager import StoryManager


manager = StoryManager()


def browse_file():
    path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt")])
    if path:
        file_var.set(path)


def submit():
    title = title_entry.get().strip()
    author = author_entry.get().strip()
    description = desc_text.get("1.0", tk.END).strip()
    file_path = file_var.get().strip()

    if not title or not file_path:
        messagebox.showerror("Error", "Title and book file are required.")
        return

    try:
        manager.add_story(title, author, description, file_path)
    except Exception as exc:  # pragma: no cover - GUI error display
        messagebox.showerror("Error", str(exc))
        return

    messagebox.showinfo("Success", "Story added to database.")
    title_entry.delete(0, tk.END)
    author_entry.delete(0, tk.END)
    desc_text.delete("1.0", tk.END)
    file_var.set("")


root = tk.Tk()
root.title("Add Story")

# Title field
tk.Label(root, text="Title:").grid(row=0, column=0, sticky="e")
title_entry = tk.Entry(root, width=50)
title_entry.grid(row=0, column=1, padx=5, pady=5)

# Author field
tk.Label(root, text="Author:").grid(row=1, column=0, sticky="e")
author_entry = tk.Entry(root, width=50)
author_entry.grid(row=1, column=1, padx=5, pady=5)

# Description field
tk.Label(root, text="Description:").grid(row=2, column=0, sticky="ne")
desc_text = tk.Text(root, width=50, height=5)
desc_text.grid(row=2, column=1, padx=5, pady=5)

# File path field
tk.Label(root, text="Book File:").grid(row=3, column=0, sticky="e")
file_var = tk.StringVar()
file_entry = tk.Entry(root, textvariable=file_var, width=40)
file_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
browse_btn = tk.Button(root, text="Browse", command=browse_file)
browse_btn.grid(row=3, column=2, padx=5, pady=5)

# Submit button
submit_btn = tk.Button(root, text="Submit", command=submit)
submit_btn.grid(row=4, column=1, pady=10)

root.mainloop()

