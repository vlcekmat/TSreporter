from tkinter import *
from tkinter.font import Font
from PIL import Image, ImageTk
import imageio
from tkinter import filedialog
import os
from threading import Thread
from time import sleep


def rewrite_textbox(message, textbox):
    # use this to clear a textbox and display a message
    textbox.configure(state=NORMAL)
    textbox.delete("1.0", END)
    textbox.insert(END, message)
    textbox.configure(state=DISABLED)


class GifMaker:
    # This class handles the frames of the gif and the gif generation
    frames = []  # list of tuples of frames that will be in the gif
    # frames[0] are PIL Images from Image.open()
    # frames[1] is a bool if the image was a png and therefore a .jpg was generated and needs to be deleted
    gif_name = ""  # this is the name that the gif will be saved under, same as first frame but .gif
    save_gifs_here = ""  # folder where the gif will be saved, should be "edited images location" from cfg

    def set_save_location(self, location):
        self.save_gifs_here = location

    def add_frame(self, image_location, was_png):
        if len(self.frames) == 0:
            self.gif_name = self.save_gifs_here + '/' + image_location.split('/')[-1][0:-4] + ".gif"
        new_frame = Image.open(image_location)  # don't forget to close
        new_frame.thumbnail((1200, 700))
        self.frames.append((new_frame, was_png))

    def remove_frame(self, index):
        remove_me = self.frames.pop(index)
        remove_me[0].close()
        if remove_me[1]:
            os.remove(remove_me[0].filename)
        if index == 0:
            if len(self.frames) == 0:
                self.gif_name = ""
            else:  # Set the gif name to be the new gif head
                self.gif_name = self.save_gifs_here + '/' + self.frames[0][0].filename.split('/')[-1][0:-4] + ".gif"

    def clear_frames(self):
        while len(self.frames) > 0:
            remove_me = self.frames.pop()
            remove_me[0].close()
            if remove_me[1]:
                os.remove(remove_me[0].filename)

        self.gif_name = ""

    def save_gif(self, fps):
        if self.gif_name != "" and len(self.frames) > 0:
            imageio.mimwrite(self.gif_name, [fr[0] for fr in self.frames], fps=fps)
            # The [...] takes makes list of 0th tuple member from self.frames (the images themselves)


class GifGeneratorPage(Frame):
    current_color_theme = None
    app = None
    gif_maker = GifMaker()
    preview_thread = None  # This thread handles the preview of the gif
    duration = 1  # The FPS of the created gif, needs to be converted from frame duration

    images_paths_frame = None  # This frame holds the textboxes with the locations of the frames and delete buttons
    widgets_to_update = []

    gif_created_text = None

    def __init__(self, app, location):
        super().__init__()
        self.dur_var = StringVar()
        self.gif_maker.set_save_location(location)
        self.pack(fill=BOTH, expand=True)
        self.app = app
        self.current_color_theme = app.current_color_theme
        self.init_widgets()

    class GifPreviewThread(Thread):
        # Handles the preview of the gif by updating the preview label with the selected frames
        # The speed at which is updates is set by the duration
        duration = 1  # FPS
        frames_to_show = []  # Frames that will make up the gif, here saved as
        label = None
        stop = False  # if true, thread stops

        def __init__(self, label):
            super().__init__()
            self.label = label

        def add_frame(self, frame_path):
            new_frame = Image.open(frame_path)
            new_frame.thumbnail((450, 280))
            new_ready_frame = ImageTk.PhotoImage(new_frame)
            new_frame.close()
            self.frames_to_show.append(new_ready_frame)

        def remove_frame(self, index):
            self.frames_to_show.pop(index)

        def clear_preview_frames(self):
            self.frames_to_show.clear()

        def run(self):
            try:
                while True:
                    if len(self.frames_to_show) == 0:  # This waits for a frame to appear
                        self.label.configure(image='')
                        sleep(0.5)
                        continue
                    for frame in self.frames_to_show:  # updates the frames
                        self.label.configure(image=frame)
                        self.label.image = frame
                        sleep(self.duration)
                    if self.stop:
                        break
            except RuntimeError:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                with open("./error_log.txt", "w", encoding='UTF-8') as error_log_file:
                    print("Writing error log")
                    error_log_file.write(f"An error occurred: ")
                    error_log_file.write(f"{exc_type} {exc_obj} {exc_tb}")

    def go_to_main_menu(self):
        self.preview_thread.stop = True
        self.gif_maker.clear_frames()
        self.pack_forget()
        self.app.main_menu = self.app.MainMenu()
        self.app.gif_page = None

    def find_image(self):
        img_tuple = filedialog.askopenfilenames(
            filetypes=[
                ("image", ".png"),
                ("image", ".jpg")
            ]
        )
        if img_tuple:
            img_list = []
            for img in img_tuple:
                img_list.append(img)
            del img_tuple
            for img in img_list:
                old_img_name = img
                new_img_name = old_img_name
                was_png = False
                if old_img_name[-4:] == ".png":
                    was_png = True
                    new_img_name = old_img_name[:-4] + ".jpg"
                    with Image.open(old_img_name) as convert_me:
                        convert_me.save(new_img_name, optimize=True, quality=85)
                self.gif_maker.add_frame(new_img_name, was_png)
                self.preview_thread.add_frame(new_img_name)
        self.update_image_list_box(master=self.app.gif_page.images_paths_frame, page=self.app.gif_page)

    def clear_gif_frames(self, images_frame):
        self.gif_maker.clear_frames()
        self.preview_thread.clear_preview_frames()
        images_frame['bg'] = self.app.current_color_theme[2]
        for w_list in self.widgets_to_update:
            for index in range(2):
                w_list[index].destroy()
        self.widgets_to_update = []

    def convert_to_gif(self):
        self.gif_maker.save_gif(self.duration)
        self.gif_created_text.pack()

    def callback(self, dur_var):
        dv = dur_var.get()
        if dv != '':
            try:
                int(dv)
            except ValueError:
                dur_var.set('1000')
                dv = '1000'
        if dv == '' or int(dv) == 0:
            dv = '1000'
        if int(dv) > 5000:
            dv = 5000
            dur_var.set('5000')
        self.duration = 1000/int(dv)
        self.preview_thread.duration = int(dv)/1000

    def destroy_widgets(self):
        for w_tuple in self.widgets_to_update:
            for item in w_tuple:
                item.destroy()
        self.widgets_to_update = []

    def update_image_list_box(self, master, page):
        self.destroy_widgets()
        index = 0
        for img_path in [f[0].filename for f in self.gif_maker.frames]:
            delete_image_button = Button(master=master, bg=page.current_color_theme[3], fg=page.current_color_theme[1],
                                         text="Delete", activebackground=page.current_color_theme[3],
                                         padx=5, pady=2, activeforeground=page.current_color_theme[1])
            img_path_text = Text(master=master, bg=page.current_color_theme[3], fg=page.current_color_theme[1],
                            font=Font(size=10), width=40, height=1, borderwidth=0)
            self.widgets_to_update.append((img_path_text, delete_image_button))
            delete_image_button.grid(row=index, column=0)
            img_path_text.grid(row=index, column=2)
            img_path_text.insert(END, img_path.split('/')[-1])
            img_path_text['state'] = DISABLED
            master['bg'] = self.app.current_color_theme[3]
            index += 1

        for widget_tuple in self.widgets_to_update:
            widget_tuple[1]['command'] = lambda i=self.widgets_to_update.index(widget_tuple): [
                self.gif_maker.remove_frame(i),
                self.preview_thread.remove_frame(i),
                self.update_image_list_box(master, page)
            ]
        if len(self.widgets_to_update) == 0:
            self.clear_gif_frames(master)

    def init_widgets(self):
        background = Frame(master=self, bg=self.current_color_theme[3])
        background.pack(fill=BOTH, expand=True)

        middle_frame = Frame(master=background, bg=self.current_color_theme[2])
        middle_frame.pack(fill=BOTH, expand=True, pady=10, padx=20)

        top_frame = Frame(master=middle_frame, bg=self.current_color_theme[2])
        top_frame.pack(fill=BOTH, expand=False, pady=0, padx=0, side=TOP)

        self.gif_created_text = Label(top_frame, bg=self.current_color_theme[2], fg=self.current_color_theme[1],
                                      text='GIF successfully created in your "Edited Images" folder!',
                                      font=Font(size=12))

        bottom_frame = Frame(master=background, bg=self.current_color_theme[3])
        bottom_frame.pack(fill=X, side=BOTTOM)

        images_list_frame = Frame(master=middle_frame, bg=self.current_color_theme[3], pady=10, padx=10)
        images_list_frame.pack(side=LEFT, padx=10, pady=10, fill="none", expand=True)
        self.images_paths_frame = images_list_frame

        preview_frame = Frame(master=middle_frame, bg=self.current_color_theme[2], pady=60, padx=20)
        preview_frame.pack(side=RIGHT, padx=0, fill="none", expand=True)

        preview_label = Label(master=preview_frame, padx=0, pady=0, bg=self.current_color_theme[2])
        preview_label.pack()
        self.preview_thread = self.GifPreviewThread(preview_label)
        self.preview_thread.start()
        self.update_image_list_box(master=images_list_frame, page=self)

        back_button = self.app.AppButton('Main Menu', frame=bottom_frame, side=LEFT,
                                         command=lambda: self.go_to_main_menu())
        convert_button = self.app.AppButton('Convert', frame=bottom_frame, side=RIGHT,
                                            command=self.convert_to_gif)
        find_button = self.app.AppButton('Find', frame=bottom_frame, side=RIGHT,
                                         command=lambda: self.find_image())
        clear_button = self.app.AppButton('Clear', frame=bottom_frame, side=RIGHT,
                                          command=lambda: self.clear_gif_frames(images_list_frame))
        fps_frame = Frame(master=bottom_frame, bg=self.current_color_theme[3])
        fps_frame.pack(side=RIGHT, padx=10)

        fps_text = Label(master=fps_frame, bg=self.current_color_theme[3], fg=self.current_color_theme[1],
                         text='Delay', font=Font(size=15)).grid(row=0, column=0)
        dur_var = StringVar()
        dur_var.set(1000)
        dur_var.trace("w", lambda name, index, mode, var=dur_var: self.callback(var))
        fps_entry = Entry(master=fps_frame, bg=self.current_color_theme[2], fg=self.current_color_theme[1],
                          width=10, font=Font(size=15), textvariable=dur_var).grid(row=1, column=0)
