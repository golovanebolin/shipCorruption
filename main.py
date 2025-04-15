import customtkinter as ctk
from tkinter import filedialog, messagebox
import math
import csv
from PIL import Image, ImageTk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DEFAULT_SCALE = 75.8  # 1 морская миля = 2 см (75.8 пикселей при 96 dpi)
PADDING = 20

class Ship:
    def __init__(self, x_nm, y_nm, speed_knots, course_deg, name, ship_class, country, is_own=False):
        self.x_nm = x_nm
        self.y_nm = y_nm
        self.speed_knots = speed_knots
        self.course_deg = course_deg
        self.name = name
        self.ship_class = ship_class
        self.country = country
        self.is_own = is_own
        
        rad = math.radians(-course_deg + 90)
        self.vx = speed_knots * math.cos(rad)
        self.vy = speed_knots * math.sin(rad)

class ShipEditor(ctk.CTkToplevel):
    def __init__(self, parent, ship=None):
        super().__init__(parent)
        self.title("Добавление судна")
        self.geometry("400x400")
        self.ship = ship
        self.result = None
        self.create_widgets()

    def create_widgets(self):
        self.grid_columnconfigure(1, weight=1)
        
        fields = [
            ("X (мили):", "x_nm"),
            ("Y (мили):", "y_nm"),
            ("Скорость (узлы):", "speed_knots"),
            ("Курс (°):", "course_deg"),
            ("Название:", "name"),
            ("Класс:", "ship_class"),
            ("Страна:", "country")
        ]
        
        self.entries = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(self, text=label).grid(row=i, column=0, padx=5, pady=5, sticky="e")
            entry = ctk.CTkEntry(self)
            entry.grid(row=i, column=1, padx=5, pady=5, sticky="ew")
            if self.ship:
                entry.insert(0, str(getattr(self.ship, key)))
            self.entries[key] = entry
        
        self.is_own = ctk.CTkCheckBox(self, text="Наше судно")
        self.is_own.grid(row=7, columnspan=2, pady=10)
        
        btn_frame = ctk.CTkFrame(self)
        btn_frame.grid(row=8, columnspan=2, pady=10)
        
        ctk.CTkButton(btn_frame, text="Сохранить", command=self.save).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Отмена", command=self.destroy).pack(side="right", padx=5)

    def save(self):
        try:
            data = {key: entry.get() for key, entry in self.entries.items()}
            self.result = (
                float(data['x_nm']),
                float(data['y_nm']),
                float(data['speed_knots']),
                float(data['course_deg']),
                data['name'],
                data['ship_class'],
                data['country'],
                self.is_own.get()
            )
            self.destroy()
        except ValueError:
            messagebox.showerror("Ошибка", "Некорректные значения")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.ships = []
        self.original_bg_image = None
        self.bg_image = None
        self.current_step = 0
        self.STEP_MESSAGES = {
            1: "Проводится анализ навигационной обстановки",
            2: "Осуществляется потоковая обработка данных",
            3: "Определяются параметры движения",
            4: "Определяются правила МППСС",
            5: "Решение найдено!"
        }
        self.setup_ui()
        
    def setup_ui(self):
        self.title("Система предотвращения столкновений судов")
        self.geometry("1400x800")
        
        # Основная рамка
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Панель управления
        control_frame = ctk.CTkFrame(main_frame, width=500)
        control_frame.pack(side="left", fill="y", padx=5, pady=5)
        
        # Параметры
        params_frame = ctk.CTkFrame(control_frame)
        params_frame.pack(pady=10, fill="x")
        
        ctk.CTkLabel(params_frame, text="Порог CPA (мили):").grid(row=0, column=0, padx=5, pady=2)
        self.cpa_entry = ctk.CTkEntry(params_frame, width=100)
        self.cpa_entry.insert(0, "1.0")
        self.cpa_entry.grid(row=0, column=1, padx=5, pady=2)
        
        ctk.CTkLabel(params_frame, text="Порог TCPA (мин):").grid(row=1, column=0, padx=5, pady=2)
        self.tcpa_entry = ctk.CTkEntry(params_frame, width=100)
        self.tcpa_entry.insert(0, "15.0")
        self.tcpa_entry.grid(row=1, column=1, padx=5, pady=2)
        
        # Управление масштабом
        scale_frame = ctk.CTkFrame(control_frame)
        scale_frame.pack(pady=10, fill="x")
        
        ctk.CTkLabel(scale_frame, text="Масштаб (пикс/миля):").grid(row=0, column=0, padx=5, pady=2)
        self.scale_entry = ctk.CTkEntry(scale_frame, width=100)
        self.scale_entry.insert(0, str(DEFAULT_SCALE))
        self.scale_entry.grid(row=0, column=1, padx=5, pady=2)
        
        self.auto_scale = ctk.CTkCheckBox(scale_frame, text="Автомасштаб")
        self.auto_scale.grid(row=1, columnspan=2, pady=5)
        
        # Управление данными
        data_buttons = ctk.CTkFrame(control_frame)
        data_buttons.pack(pady=10, fill="x")
        
        ctk.CTkButton(data_buttons, text="Добавить судно", command=self.add_ship).pack(fill="x", pady=2)
        ctk.CTkButton(data_buttons, text="Удалить судно", command=self.remove_ship).pack(fill="x", pady=2)
        ctk.CTkButton(data_buttons, text="Импорт CSV", command=self.import_csv).pack(fill="x", pady=2)
        ctk.CTkButton(data_buttons, text="Экспорт CSV", command=self.export_csv).pack(fill="x", pady=2)
        
        # Таблица судов
        self.tree = ctk.CTkScrollableFrame(control_frame, height=200,width=500)
        self.tree.pack(fill="both", expand=True, pady=10)
        
        # Заголовки таблицы
        headers = ["Название", "Класс", "Страна", "X (мили)", "Y (мили)", "Скорость", "Курс"]
        for i, header in enumerate(headers):
            label = ctk.CTkLabel(self.tree, text=header, font=("Arial", 12, "bold"))
            label.grid(row=0, column=i, padx=5, pady=2)
        
        # Шаги обработки
        steps_frame = ctk.CTkFrame(control_frame)
        steps_frame.pack(fill="x", pady=10)
        
        self.step_buttons = []
        for i in range(1, 6):
            btn = ctk.CTkButton(
                steps_frame, 
                text=f"{i}) {self.step_button_text(i)}",
                command=lambda i=i: self.run_step(i)
            )
            btn.pack(fill="x", pady=2)
            self.step_buttons.append(btn)
        
        # Статус
        self.status_label = ctk.CTkLabel(control_frame, text="", anchor="w")
        self.status_label.pack(fill="x", pady=5)
        
        # Холст
        self.canvas = ctk.CTkCanvas(main_frame, bg="#2b2b2b")
        self.canvas.pack(side="right", fill="both", expand=True, padx=5, pady=5)
        
        # Загрузка карты
        ctk.CTkButton(control_frame, text="Загрузить карту", command=self.load_background).pack(fill="x", pady=5)

    def step_button_text(self, step):
        texts = {
            1: "Анализ обстановки",
            2: "Обработка данных",
            3: "Параметры движения",
            4: "Правила МППСС",
            5: "Решение"
        }
        return texts[step]

    def add_ship(self):
        editor = ShipEditor(self)
        self.wait_window(editor)
        if editor.result:
            data = editor.result
            ship = Ship(*data)
            self.ships.append(ship)
            self.update_table()
            self.update_map()

    def remove_ship(self):
        if not self.ships:
            return
        self.ships.pop()
        self.update_table()
        self.update_map()

    def update_table(self):
        for widget in self.tree.winfo_children()[7:]:
            widget.destroy()
        
        for i, ship in enumerate(self.ships):
            ctk.CTkLabel(self.tree, text=ship.name).grid(row=i+1, column=0, padx=5)
            ctk.CTkLabel(self.tree, text=ship.ship_class).grid(row=i+1, column=1, padx=5)
            ctk.CTkLabel(self.tree, text=ship.country).grid(row=i+1, column=2, padx=5)
            ctk.CTkLabel(self.tree, text=f"{ship.x_nm:.2f}").grid(row=i+1, column=3, padx=5)
            ctk.CTkLabel(self.tree, text=f"{ship.y_nm:.2f}").grid(row=i+1, column=4, padx=5)
            ctk.CTkLabel(self.tree, text=f"{ship.speed_knots:.1f}").grid(row=i+1, column=5, padx=5)
            ctk.CTkLabel(self.tree, text=f"{ship.course_deg:.1f}°").grid(row=i+1, column=6, padx=5)

    def import_csv(self):
        filepath = filedialog.askopenfilename(filetypes=[("CSV файлы", "*.csv")])
        if filepath:
            try:
                with open(filepath, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    self.ships = []
                    for row in reader:
                        ship = Ship(
                            x_nm=float(row['x_nm']),
                            y_nm=float(row['y_nm']),
                            speed_knots=float(row['speed_knots']),
                            course_deg=float(row['course_deg']),
                            name=row['name'],
                            ship_class=row['ship_class'],
                            country=row['country'],
                            is_own=row.get('is_own', 'False') == 'True'
                        )
                        self.ships.append(ship)
                    self.update_table()
                    self.update_map()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка импорта: {str(e)}")

    def export_csv(self):
        filepath = filedialog.asksaveasfilename(defaultextension=".csv")
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['x_nm', 'y_nm', 'speed_knots', 'course_deg', 
                                   'name', 'ship_class', 'country', 'is_own'])
                    for ship in self.ships:
                        writer.writerow([
                            ship.x_nm,
                            ship.y_nm,
                            ship.speed_knots,
                            ship.course_deg,
                            ship.name,
                            ship.ship_class,
                            ship.country,
                            ship.is_own
                        ])
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка экспорта: {str(e)}")

    def load_background(self):
        filepath = filedialog.askopenfilename()
        if filepath:
            try:
                self.original_bg_image = Image.open(filepath)
                self.update_background_scale()
            except Exception as e:
                messagebox.showerror("Ошибка", f"Ошибка загрузки: {str(e)}")

    def update_background_scale(self):
        if self.original_bg_image:
            try:
                scale = float(self.scale_entry.get()) / DEFAULT_SCALE
                width = int(self.original_bg_image.width * scale)
                height = int(self.original_bg_image.height * scale)
                resized = self.original_bg_image.resize((width, height), Image.Resampling.LANCZOS)
                self.bg_image = ImageTk.PhotoImage(resized)
                self.canvas.config(width=width, height=height)
                self.canvas.create_image(0, 0, anchor="nw", image=self.bg_image)
            except ValueError:
                pass

    def run_step(self, step):
        self.current_step = step
        self.update_map()
        self.status_label.configure(text=self.STEP_MESSAGES.get(step, ""))

    def update_map(self):
        self.canvas.delete("all")
        
        if self.original_bg_image:
            self.canvas.create_image(0, 0, anchor="nw", image=self.bg_image)
        
        try:
            current_scale = float(self.scale_entry.get())
            own_ship = next((ship for ship in self.ships if ship.is_own), None)
            
            for ship in self.ships:
                x = PADDING + ship.x_nm * current_scale
                y = self.canvas.winfo_height() - PADDING - ship.y_nm * current_scale
                
                color = "green" if ship.is_own else "blue"
                show_text = self.current_step >= 3
                show_vector = self.current_step >= 3
                dangerous = False

                if self.current_step >= 4 and not ship.is_own and own_ship:
                    cpa, tcpa = self.calculate_cpa_tcpa(own_ship, ship)
                    cpa_threshold = float(self.cpa_entry.get())
                    tcpa_threshold = float(self.tcpa_entry.get())
                    dangerous = cpa <= cpa_threshold and tcpa <= tcpa_threshold
                    color = "red" if dangerous else "blue"

                # Отрисовка судна
                if self.current_step >= 1:
                    self.canvas.create_oval(
                        x-5, y-5, x+5, y+5,
                        fill="red" if dangerous else color,
                        outline="white"
                    )

                # Вектор движения
                if show_vector:
                    end_x = x + ship.vx * 5
                    end_y = y - ship.vy * 5
                    self.canvas.create_line(
                        x, y, end_x, end_y,
                        arrow=ctk.LAST,
                        fill=color,
                        width=2
                    )

                # Текст
                if show_text:
                    text = f"{ship.name}\n{ship.speed_knots:.1f} узлов"
                    if self.current_step >= 4 and own_ship:
                        cpa, tcpa = self.calculate_cpa_tcpa(own_ship, ship)
                        text += f"\nCPA: {cpa:.2f} миль\nTCPA: {tcpa:.1f} мин"
                    self.canvas.create_text(
                        x, y-30,
                        text=text,
                        fill=color,
                        anchor=ctk.S,
                        font=("Arial", 9))
        
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка отрисовки: {str(e)}")

    def calculate_cpa_tcpa(self, ship1, ship2):
        dx = ship2.x_nm - ship1.x_nm
        dy = ship2.y_nm - ship1.y_nm
        dvx = ship2.vx - ship1.vx
        dvy = ship2.vy - ship1.vy
        
        dv_squared = dvx**2 + dvy**2
        if dv_squared == 0:
            return (math.hypot(dx, dy), 0)
        
        tcpa = -(dx*dvx + dy*dvy) / dv_squared
        tcpa = max(tcpa, 0)
        
        closest_x = dx + dvx * tcpa
        closest_y = dy + dvy * tcpa
        cpa = math.hypot(closest_x, closest_y)
        
        return (cpa, tcpa * 60)

if __name__ == "__main__":
    app = App()
    app.mainloop()