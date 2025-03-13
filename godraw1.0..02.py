from tkinter import Tk, Button, Scale, Canvas, Label, StringVar, Listbox, Toplevel, messagebox, Frame, Scrollbar, END, NW, Frame
from tkinter.colorchooser import askcolor
from tkinter.simpledialog import askinteger
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageDraw, ImageTk
from PyQt5.QtGui import QImage, QPainter, QColor
from PyQt5.QtCore import Qt

class Tile:
    def __init__(self, x, y, image):
        self.x = x  # Tile's position in the grid
        self.y = y
        self.image = image  # A PhotoImage or PIL image object

class Paint:
    DEFAULT_COLOR = 'black'
    GRID_SIZE = 16
    PIXEL_SIZE = 30

    def __init__(self):
        self.root = ttk.Window(themename="vapor")
        self.root.title("GoDraw Sprite Editor")

        # Initialize attributes
        self.x = 0  # Tile's position in the grid
        self.y = 0
        
        self.layers = []  # List of canvases for layers
        self.active_layer_index = 0
        self.color = self.DEFAULT_COLOR
        self.canvas_width = self.GRID_SIZE * self.PIXEL_SIZE
        self.canvas_height = self.GRID_SIZE * self.PIXEL_SIZE
        self.undo_stack = []
        self.redo_stack = []
        self.frames = []
        self.is_playing = False

        # Setup UI
        self.setup_ui()

        # Create the first (base) layer
        self.add_layer()

        self.root.mainloop()

    def setup_ui(self):
        """Setup UI components."""
        
        #grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=1)

        # Left toolbar frame
        toolbar = Frame(self.root)
        toolbar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)
        # Pen, Eraser, and Color tools
        Button(toolbar, text='Pen', command=self.use_pen).pack(fill='x', pady=2)
        Button(toolbar, text='Eraser', command=self.use_eraser).pack(fill='x', pady=2)
        Button(toolbar, text='Color', command=self.choose_color).pack(fill='x', pady=2)
        #scrollableframe
        self.canvas_frame = Frame(self.root)
        self.canvas_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        # Pan Tool Button
        Button(toolbar, text='Pan Tool', command=self.use_pan).pack(fill='x', pady=2)
        # Brush size slider
        self.size_scale = Scale(toolbar, from_=1, to=10, orient='horizontal', label="Brush Size")
        self.size_scale.pack(fill='x', pady=5)

        # Layer management
        Button(toolbar, text='Add Layer', command=self.add_layer).pack(fill='x', pady=2)
        Button(toolbar, text='Clear Layer', command=self.clear_canvas).pack(fill='x', pady=2)
        Button(toolbar, text='Merge Layers', command=self.merge_layers).pack(fill='x', pady=2)

        # Save and Undo/Redo
        Button(toolbar, text='Save', command=self.save_file).pack(fill='x', pady=2)
        Button(toolbar, text='Undo', command=self.undo).pack(fill='x', pady=2)
        Button(toolbar, text='Redo', command=self.redo).pack(fill='x', pady=2)

        # Animation controls
        Button(toolbar, text='Save Frame', command=self.save_frame).pack(fill='x', pady=2)
        Button(toolbar, text='Play Animation', command=self.play_animation).pack(fill='x', pady=2)
        Button(toolbar, text='Export GIF', command=self.export_as_gif).pack(fill='x', pady=2)
        
        self.zoom_scale = Scale(toolbar, from_=1, to=5, orient='horizontal', label="Zoom Level")
        self.zoom_scale.set(1)  # Default zoom level
        self.zoom_scale.pack(fill='x', pady=5)
        self.zoom_scale.bind("<Motion>", self.update_zoom)  # Bind the zoom update function
     # Canvas with scrollbars
        self.canvas = Canvas(self.canvas_frame, bg="white", width=self.canvas_width, height=self.canvas_height,
                            scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.v_scrollbar = Scrollbar(self.canvas_frame, orient="vertical", command=self.canvas.yview)
        self.v_scrollbar.grid(row=0, column=1, sticky="ns")
        self.h_scrollbar = Scrollbar(self.canvas_frame, orient="horizontal", command=self.canvas.xview)
        self.h_scrollbar.grid(row=1, column=0, sticky="ew")

        self.canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)


        # Bind pan functionality
        self.canvas.bind('<ButtonPress-3>', self.start_pan)
        self.canvas.bind('<B3-Motion>', self.pan)

        # Configure canvas frame to resize properly
        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)
            # Bind drawing to the main canvas
        self.bind_canvas_events(self.canvas)
        

        # Layer listbox
        Label(toolbar, text="Layers:").pack(anchor='w', pady=5)
        self.layer_listbox = Listbox(toolbar, height=5)
        self.layer_listbox.pack(fill='x', pady=2)
        self.layer_listbox.bind('<<ListboxSelect>>', self.switch_layer)

        # Status label
        self.var_status = StringVar(value='Selected Tool: Pen')
        Label(toolbar, textvariable=self.var_status).pack(fill='x', pady=5)

        # Grid area (center)
        self.canvas_frame = Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="white")
        self.canvas_frame.grid(row=0, column=1, padx=10, pady=10)

        Button(toolbar, text='Flood Fill', command=self.use_flood_fill).pack(fill='x', pady=2)

        Button(toolbar, text='Adjust Grid Size', command=self.adjust_grid_size).pack(fill='x', pady=2)

        color_frame = Frame(self.root)
        color_frame.grid(row=5, column=0, columnspan=4, pady=10)  # Adjust row/column as needed

        colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF', '#000000', '#FFFFFF']
        for color in colors:
            color_button = Button(color_frame, bg=color, width=2, height=1,
                                command=lambda c=color: self.set_color(c))
            color_button.pack(side='left', padx=2)

    def draw_grid(self, canvas):
        """Draw the grid on a given canvas."""
        for row in range(self.GRID_SIZE):
            for col in range(self.GRID_SIZE):
                x1 = col * self.PIXEL_SIZE
                y1 = row * self.PIXEL_SIZE
                x2 = x1 + self.PIXEL_SIZE
                y2 = y1 + self.PIXEL_SIZE
                canvas.create_rectangle(x1, y1, x2, y2, outline="lightgray", fill="white",
                                        tags=(f"pixel-{row}-{col}", "grid"))
    def create_tiles(self):
        """Generate tiles for the grid."""
        self.tiles = []
        tile_size = 256  # Size of each tile in pixels
        rows = (self.canvas_height + tile_size - 1) // tile_size
        cols = (self.canvas_width + tile_size - 1) // tile_size

        for row in range(rows):
            for col in range(cols):
                # Create a blank or default image for now
                image = Image.new("RGBA", (tile_size, tile_size), "white")
                self.tiles.append(Tile(col * tile_size, row * tile_size, ImageTk.PhotoImage(image)))

    def visible_tiles(self):
        """Yield visible tiles based on canvas viewport."""
        tile_size = 256  # Match the tile size used earlier

        # Get the scroll position
        x0, y0, x1, y1 = self.canvas.bbox("all")  # Viewport bounds in canvas coordinates

        # Determine the range of tiles visible
        start_col = x0 // tile_size
        end_col = (x1 + tile_size - 1) // tile_size
        start_row = y0 // tile_size
        end_row = (y1 + tile_size - 1) // tile_size

        for tile in self.tiles:
            if start_col <= tile.x // tile_size <= end_col and start_row <= tile.y // tile_size <= end_row:
                yield tile
    
    def render_tiles(self):
        """Render visible tiles on the canvas."""
        self.canvas.delete("tile")  # Remove existing tiles tagged as "tile"

        for tile in self.visible_tiles():
            self.canvas.create_image(tile.x, tile.y, anchor=NW, image=tile.image, tags="tile")

    def adjust_grid_size(self):
        """Prompt user to adjust the grid size and update all canvases."""
        new_grid_size = askinteger("Grid Size", "Enter new grid size (e.g., 16):", minvalue=1, maxvalue=150)
        if new_grid_size:
            self.GRID_SIZE = new_grid_size

            # Recalculate pixel size dynamically to ensure the grid fills the window
            self.PIXEL_SIZE = min(self.canvas_width // self.GRID_SIZE, self.canvas_height // self.GRID_SIZE)
            # Calculate canvas dimensions to fill the window
            self.canvas_width = self.GRID_SIZE * self.PIXEL_SIZE
            self.canvas_height = self.GRID_SIZE * self.PIXEL_SIZE

            for layer in self.layers:
                layer.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
                layer.delete("all")  # Clear the layer
                self.draw_grid(layer)  # Redraw the grid
                 # Update scrollbars for the active layer
                self.setup_layer_bindings(self.layers[self.active_layer_index])
                # Update scrollbars for the active layer
                active_canvas = self.layers[self.active_layer_index]
                self.v_scrollbar.config(command=active_canvas.yview)
                self.h_scrollbar.config(command=active_canvas.xview)

            
        active_canvas.delete("all")  # Clear the old grid
        self.draw_grid(active_canvas)
           
    def update_zoom(self, event=None):
        """Update the zoom level and redraw the grid."""


        zoom_level = self.zoom_scale.get()  # Get zoom level from slider
        self.PIXEL_SIZE = 20 * zoom_level   # Base pixel size is 20, scale it up/down

        # Update canvas dimensions based on new pixel size
        self.canvas_width = self.GRID_SIZE * self.PIXEL_SIZE
        self.canvas_height = self.GRID_SIZE * self.PIXEL_SIZE

           # Save the current state of the active canvas
        active_canvas = self.layers[self.active_layer_index]
        current_state = self.capture_canvas_state(active_canvas)
        
        # Update all layers
        for layer in self.layers:
            
            layer.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
            layer.delete("all")  # Clear existing grid
            self.draw_grid(layer)  # Redraw the grid
        
        self.apply_canvas_state(current_state,layer)    # Apply to the same layer
  

  
    def use_pan(self):
        """Activate the pan tool."""
        self.var_status.set("Selected Tool: Pan")
        for layer in self.layers:
            layer.unbind('<Button-1>')
            layer.unbind('<Button-1>')
        self.canvas.bind('<ButtonPress-1>', self.start_pan)
        self.canvas.bind('<B1-Motion>', self.pan)
        self.refresh_scrollbars()

    def start_pan(self, event):
        """Record the starting point for panning."""
        self.layers[self.active_layer_index].scan_mark(event.x,event.y) 
    

    def pan(self, event):
        """Handle panning."""
        self.layers[self.active_layer_index].scan_dragto(event.x, event.y, gain=1)
        self.refresh_scrollbars()
        
    def paint_tile(self, x, y, color):
        """Modify a specific tile."""
        tile_size = 256
        col, row = x // tile_size, y // tile_size
        tile = self.get_tile(col, row)  # Find the correct tile
        draw = ImageDraw.Draw(tile.image)  # Modify the tile's image
        draw.rectangle([x % tile_size, y % tile_size, (x % tile_size) + 10, (y % tile_size) + 10], fill=color)
        tile.image = ImageTk.PhotoImage(tile.image)  # Update the tile image


    def set_color(self, color):
        """Set the active drawing color."""
        self.color = color
        self.var_status.set(f"Selected Color: {color}")

    
    def add_layer(self):
        """Add a new layer and configure its size and scrollbars."""
        new_canvas = Canvas(self.canvas_frame, bg="white",
                            width=self.canvas_width, height=self.canvas_height,
                            scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        new_canvas.grid(row=0, column=0, sticky="nsew")

        if self.layers:
            self.layers[self.active_layer_index].grid_remove()

        self.layers.append(new_canvas)
        self.active_layer_index = len(self.layers) - 1

        # Set up bindings for the new canvas
        self.setup_layer_bindings(new_canvas)

        # Draw the grid
        self.draw_grid(new_canvas)

        

        self.refresh_scrollbars()

        # Add layer name to the listbox
        self.layer_listbox.insert("end", f"Layer {len(self.layers)}")

        # Update scrollbars for the new canvas
       # new_canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.v_scrollbar.config(command=new_canvas.yview)
        self.h_scrollbar.config(command=new_canvas.xview)

    def bind_canvas_events(self, canvas):
        """Bind events to the canvas for painting."""
        canvas.bind('<B3-Motion>', self.paint_pixel)  # Bind for painting while dragging
        canvas.bind('<Button-3>', self.paint_pixel)   # Bind for painting on click


    def switch_layer(self, event):
        """Switch to a selected layer."""
        selected_index = self.layer_listbox.curselection()
        if not selected_index:
            return

        # Hide the current layer
        self.layers[self.active_layer_index].grid_remove()

        # Show the selected layer
        self.active_layer_index = selected_index[0]
        active_canvas = self.layers[self.active_layer_index]
        active_canvas.grid(row=0, column=0, sticky="nsew")

        # Update scrollbar links
        active_canvas.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.v_scrollbar.config(command=active_canvas.yview)
        self.h_scrollbar.config(command=active_canvas.xview)

    def setup_layer_bindings(self,layer):
       """Bind scrollbars and events to the given canvas."""
       layer.config(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
       self.v_scrollbar.config(command=layer.yview)
       self.h_scrollbar.config(command=layer.xview)

        # Bind events for painting
       self.bind_canvas_events(layer)

        # Bind events for panning
       layer.bind('<ButtonPress-3>', self.start_pan)  # Right mouse button to start panning
       layer.bind('<B3-Motion>', self.pan)  # Drag with right mouse button to pan

       # Update scroll region for the active canvas
       active_canvas = self.layers[self.active_layer_index]
       active_canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
       self.v_scrollbar.config(command=active_canvas.yview)
       self.h_scrollbar.config(command=active_canvas.xview)

    def merge_layers(self):
        """Merge all layers into the active layer on the canvas."""
        if not self.layers:
            messagebox.showinfo("Merge Layers", "No layers to merge.")
            return

        # Get the active layer to merge everything onto
        active_canvas = self.layers[self.active_layer_index]

        # Loop through all layers and merge their contents onto the active canvas
        for i, canvas in enumerate(self.layers):
            if i == self.active_layer_index:
                continue  # Skip the active layer itself

            # Copy each pixel from this layer to the active layer
            for item in canvas.find_withtag("grid"):
                coords = canvas.coords(item)
                if len(coords) == 4:  # Only process rectangle items
                    x1, y1, x2, y2 = map(int, coords)
                    color = canvas.itemcget(item, "fill")
                    if color != "white":  # Ignore white pixels
                        active_canvas.itemconfig(f"pixel-{y1 // self.PIXEL_SIZE}-{x1 // self.PIXEL_SIZE}", fill=color)

        # Clear all other layers and keep only the active one
        for i, canvas in enumerate(self.layers):
            if i != self.active_layer_index:
                canvas.delete("all")

        # Reset layers list to only contain the active layer
        self.layers = [active_canvas]
        self.layer_listbox.delete(0, "end")
        self.layer_listbox.insert("end", "Merged Layer")
        self.active_layer_index = 0
        messagebox.showinfo("Merge Layers", "All layers merged into the active layer.")


    def capture_canvas_state(self,canvas):
        """Capture the current state of the active layer."""
        
        state = {}
        for item in canvas.find_withtag("grid"):
            coords = canvas.coords(item)
            if len(coords) == 4:
                row = int(coords[1] // self.PIXEL_SIZE)
                col = int(coords[0] // self.PIXEL_SIZE)
                color = canvas.itemcget(item, "fill")
                if color != "white":
                    state[(row, col)] = color
        return state
    
        
    def save_state(self):
        """Save the current state to the undo stack and clear the redo stack."""
        active_canvas = self.layers[self.active_layer_index]  # Get the active canvas
        self.state = self.capture_canvas_state(active_canvas)  # Pass the active canvas
       # if not self.undo_stack or current_state != self.undo_stack[-1]:
          #  self.undo_stack.append(current_state)
           # self.redo_stack.clear()  # Clear redo stack on a new action
           # print(f"State saved. Undo stack size: {len(self.undo_stack)}")

    def do_state_save(self):
        if not self.drawing_changes:
            return

        current_state = self.capture_canvas_state()


        if not self.undo_stack or current_state != self.undo_stack[-1]:
            self.undo_stack.append(current_state)
            self.redo_stack.clear()

        print(f"State saved. Undo stack size: {len(self.undo_stack)}")

    def bind_canvas_events(self, canvas):
        canvas.bind('<B3-Motion>', self.paint_pixel)
        canvas.bind('<Button-3>', self.paint_pixel)

    def paint_pixel(self, event):
        """Paint pixels on the canvas."""
        active_canvas = self.layers[self.active_layer_index]

        # Convert event coordinates to actual canvas coordinates
        x = active_canvas.canvasx(event.x)
        y = active_canvas.canvasy(event.y)

        # Determine the grid cell to paint
        col = int(x // self.PIXEL_SIZE)
        row = int(y // self.PIXEL_SIZE)
        
        if event.type == "4":
            self.drawing_changes = []
            self.save_state()

        brush_size = self.size_scale.get()  # Get the brush size from the scale
        color = self.color if not self.eraser_on else "white"

        # Draw multiple pixels based on brush size
        for r in range(row, row + brush_size):
            for c in range(col, col + brush_size):
                # Ensure the drawn pixel is within the grid bounds
                if 0 <= c < self.GRID_SIZE and 0 <= r < self.GRID_SIZE:
                    active_canvas.itemconfig(f"pixel-{r}-{c}", fill=color)
                    self.drawing_changes.append((r,c,color))

    def update_canvas_grid(self):
        self.canvas_width = self.GRID_SIZE * self.PIXEL_SIZE
        self.canvas_height = self.GRID_SIZE * self.PIXEL_SIZE

        # Clear all items and reconfigure canvas
        self.canvas.delete("all")  # Ensure the old grid is removed
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.draw_grid(self.canvas)

        # Update the canvas size and scrollregion
        self.canvas.config(scrollregion=(0, 0, self.canvas_width, self.canvas_height))
        self.canvas.delete("all")
        self.draw_grid(self.canvas)

    # Force the canvas to respect the scrollbars' positions
        self.force_resize()

    def force_resize(self):
        """Force canvas layout recalculation."""
        self.canvas.update_idletasks()


    
    def restore_canvas_state(self, state):
        """Restore a canvas state."""
        canvas = self.layers[self.active_layer_index]
        for (row, col), color in state.items():
            pixel_tag = f"pixel-{row}-{col}"
            canvas.itemconfig(pixel_tag, fill=color)

    def undo(self):
        """Undo the last action."""
        if self.undo_stack:
            current_state = self.capture_canvas_state()
            self.redo_stack.append(current_state)
            prev_state = self.undo_stack.pop()
            self.restore_canvas_state(prev_state)
            self.drawing_changes = []
            print(f"Undo stack size: {len(self.undo_stack)}, Redo stack size: {len(self.redo_stack)}")

    def redo(self):
        """Redo the last undone action."""
        if self.redo_stack:
            current_state = self.capture_canvas_state()
            self.undo_stack.append(current_state)

            next_state = self.redo_stack.pop()
            self.restore_canvas_state(next_state)
            
            print(f"Undo stack size: {len(self.undo_stack)}, Redo stack size: {len(self.redo_stack)}")

    def rebind_canvas_events(self):
        """Reset canvas bindings to the default paint behavior."""
        for canvas in self.layers:
            self.bind_canvas_events(canvas)


    def clear_canvas(self):
        """Clear the entire current layer including the grid and any drawn pixels."""
        canvas = self.layers[self.active_layer_index]
        
        # Delete all items on the canvas (both grid and drawn pixels)
        canvas.delete("all")
        
        # Redraw the grid to the cleared canvas
        self.draw_grid(canvas)
        self.save_state()

    def flood_fill(self, event):
        """Flood-fill operation starting from the clicked pixel."""
        self.save_state()
        canvas = self.layers[self.active_layer_index]
        col = event.x // self.PIXEL_SIZE
        row = event.y // self.PIXEL_SIZE

    # Get the color of the starting pixel
        start_pixel_tag = f"pixel-{row}-{col}"
        start_color = canvas.itemcget(start_pixel_tag, "fill")

    # If the starting pixel is already the target color, do nothing
        if start_color == self.color:
            return

    # Stack for storing pixels to process
        stack = [(row, col)]

        while stack:
            r, c = stack.pop()
            pixel_tag = f"pixel-{r}-{c}"

            # Skip if pixel is out of bounds or already the target color
            if not (0 <= r < self.GRID_SIZE and 0 <= c < self.GRID_SIZE):
                continue
            if canvas.itemcget(pixel_tag, "fill") != start_color:
                continue

            # Change the color of the current pixel
            canvas.itemconfig(pixel_tag, fill=self.color)

            # Add neighboring pixels to the stack
            stack.extend([(r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)])
        
    def use_flood_fill(self):
        """Activate the flood-fill tool."""
        self.eraser_on = False
        self.var_status.set("Selected Tool: Flood Fill")
        for canvas in self.layers:
            canvas.bind('<Button-1>', self.flood_fill)
        self.save_state()
    def choose_color(self):
            """Choose a new drawing color."""
            self.eraser_on = False
            color = askcolor(color=self.color)
            if color[1]:
                self.color = color[1]
        
    def use_pen(self):
        """Switch to pen tool."""
        self.eraser_on = False
        self.var_status.set("Selected Tool: Pen")
        for canvas in self.layers:
            canvas.bind('<Button-1>', self.paint_pixel)  # Save state in paint_pixel
            canvas.bind('<B1-Motion>', self.paint_pixel)
        self.save_state()
    def use_eraser(self):
        """Switch to eraser tool."""
        self.eraser_on = True
        self.var_status.set("Selected Tool: Eraser")
        for canvas in self.layers:
            canvas.bind('<Button-1>', self.paint_pixel)  
            canvas.bind('<B1-Motion>', self.paint_pixel)
        self.save_state()    
    def capture_canvas_state(self,canvas):
            """Capture the current state of the canvas (grid colors)."""
            
            state = {}
            for item in canvas.find_withtag("grid"):
                coords = canvas.coords(item)
                
                if len(coords) == 4:
                     row = int(coords[1] // self.PIXEL_SIZE)  # Calculate the row
                     col = int(coords[0] // self.PIXEL_SIZE)
                     color = canvas.itemcget(item, "fill")
                     if color != "white":
                        state[(row, col)] = color
            return state

    def apply_canvas_state(self, state,canvas):
            """Apply a saved state to the canvas."""
            for (row, col), color in state.items():
                
                # Translate logical grid coordinates into visual pixel coordinates
                x1 = col * self.PIXEL_SIZE
                y1 = row * self.PIXEL_SIZE
                x2 = x1 + self.PIXEL_SIZE
                y2 = y1 + self.PIXEL_SIZE
                canvas.create_rectangle(x1, y1, x2, y2, outline="lightgray", fill=color,
                                        tags=(f"pixel-{row}-{col}", "grid"))

    def flip_horizontal(self):
            """Flip the canvas horizontally."""
            state = self.capture_canvas_state()
            flipped_state = {(row, self.GRID_SIZE - col - 1): color for (row, col), color in state.items()}
            self.apply_canvas_state(flipped_state)

    def flip_vertical(self):
            """Flip the canvas vertically."""
            state = self.capture_canvas_state()
            flipped_state = {(self.GRID_SIZE - row - 1, col): color for (row, col), color in state.items()}
            self.apply_canvas_state(flipped_state)

    def rotate_90(self):
            """Rotate the canvas 90° clockwise."""
            state = self.capture_canvas_state()
            rotated_state = {(col, self.GRID_SIZE - row - 1): color for (row, col), color in state.items()}
            self.apply_canvas_state(rotated_state)

#-------------------------------------------------- Frame/Animation Functionality --------------------------------------------

    def save_frame(self):
        """Save the current canvas state as an in-memory frame."""
        canvas = self.layers[self.active_layer_index]
        image = Image.new("RGBA", (self.canvas_width, self.canvas_height), "white")
        draw = ImageDraw.Draw(image)

        # Draw canvas items on the image
        for item in canvas.find_withtag("grid"):
            coords = canvas.coords(item)
            if len(coords) == 4:  # Handle rectangle items
                x1, y1, x2, y2 = map(int, coords)
                color = canvas.itemcget(item, "fill")
                if color != "white":
                    draw.rectangle([x1, y1, x2, y2], fill=color)

        # Save the image in the in-memory list
        self.frames.append(image)
        messagebox.showinfo("Save Frame", f"Frame {len(self.frames)} saved.")

    def delete_frame(self):
        """Delete a selected frame."""
        selected = self.frame_listbox.curselection()
        if selected:
            index = selected[0]
            del self.frames[index]
            self.update_frame_list()

    def play_animation(self):
        """Play saved frames as an animation in a separate window."""
        if not self.frames:
            messagebox.showinfo("Animation", "No frames to play.")
            return

        # Create a new Toplevel window for the animation preview
        self.animation_window = Toplevel(self.root)
        self.animation_window.title("Animation Preview")
        self.animation_window.geometry(f"{self.canvas_width}x{self.canvas_height}")
        self.animation_window.protocol("WM_DELETE_WINDOW", self.stop_animation)  # Stop animation on close

        # Add a Label to display frames
        self.animation_label = Label(self.animation_window)
        self.animation_label.pack()

        # Create a slider to adjust animation speed
        self.speed_scale = Scale(self.animation_window, from_=10, to=500, 
                                orient='horizontal', label='Speed (ms/frame)')
        self.speed_scale.set(100)  # Default speed
        self.speed_scale.pack()

        # Start animation
        self.is_playing = True
        self.current_frame_index = 0
        self.animate_frames()

    def animate_frames(self):
        """Display frames in the animation window."""
        if not self.is_playing or self.current_frame_index >= len(self.frames):
            self.current_frame_index = 0  # Restart animation
            if not self.is_playing:
                return

        # Convert the current frame to a PhotoImage
        frame_image = ImageTk.PhotoImage(self.frames[self.current_frame_index])
        self.animation_label.config(image=frame_image)
        self.animation_label.image = frame_image  # Keep a reference to avoid garbage collection

        # Move to the next frame
        self.current_frame_index += 1

        # Schedule the next frame based on the speed slider
        speed = self.speed_scale.get()  # Get the speed value from the slider
        self.animation_window.after(speed, self.animate_frames)


    def stop_animation(self):
        """Stop the animation and close the preview window."""
        self.is_playing = False
        if hasattr(self, 'animation_window') and self.animation_window.winfo_exists():
            self.animation_window.destroy()


    def update_frame_listbox(self):
        """Update the Listbox to reflect the current frames."""
        self.frame_listbox.delete(0, END)  # Clear the listbox
        for idx, frame in enumerate(self.frames):
            self.frame_listbox.insert(END, f"Frame {idx + 1}")

    def refresh_scrollbars(self):
        """Refresh scrollbar configuration for the active canvas."""
        active_canvas = self.layers[self.active_layer_index]
        self.v_scrollbar.config(command=active_canvas.yview)
        self.h_scrollbar.config(command=active_canvas.xview)

    def select_frame(self, event):
        """Select a frame from the Listbox."""
        try:
            selected_index = self.frame_listbox.curselection()[0]
            self.current_frame_index = selected_index
            self.canvas_image = ImageTk.PhotoImage(self.frames[selected_index])
            self.canvas.create_image(0, 0, anchor=NW, image=self.canvas_image)
        except IndexError:
            pass  # No selection made

    def delete_frame(self):
        """Delete the selected frame."""
        try:
            selected_index = self.frame_listbox.curselection()[0]
            del self.frames[selected_index]
            self.update_frame_listbox()
        except IndexError:
            messagebox.showinfo("Delete Frame", "No frame selected.")

    def duplicate_frame(self):
        """Duplicate the selected frame."""
        try:
            selected_index = self.frame_listbox.curselection()[0]
            self.frames.insert(selected_index + 1, self.frames[selected_index].copy())
            self.update_frame_listbox()
        except IndexError:
            messagebox.showinfo("Duplicate Frame", "No frame selected.")

    def move_frame_up(self):
        """Move the selected frame up in the order."""
        try:
            selected_index = self.frame_listbox.curselection()[0]
            if selected_index > 0:
                self.frames[selected_index], self.frames[selected_index - 1] = (
                    self.frames[selected_index - 1],
                    self.frames[selected_index],
                )
                self.update_frame_listbox()
                self.frame_listbox.select_set(selected_index - 1)
        except IndexError:
            messagebox.showinfo("Move Frame", "No frame selected or already at the top.")

    def move_frame_down(self):
        """Move the selected frame down in the order."""
        try:
            selected_index = self.frame_listbox.curselection()[0]
            if selected_index < len(self.frames) - 1:
                self.frames[selected_index], self.frames[selected_index + 1] = (
                    self.frames[selected_index + 1],
                    self.frames[selected_index],
                )
                self.update_frame_listbox()
                self.frame_listbox.select_set(selected_index + 1)
        except IndexError:
            messagebox.showinfo("Move Frame", "No frame selected or already at the bottom.")




    def save_file(self):
        """Save the current layer as an image using PyQt5."""
        # Create a QImage to capture the canvas drawing
        image = QImage(self.canvas_width, self.canvas_height, QImage.Format_ARGB32)
        image.fill(Qt.white)  # Set background to white        

            # Use QPainter to render the current canvas to the QImage
        painter = QPainter(image)
        current_canvas = self.layers[self.active_layer_index]

            # Loop through each pixel and draw it using the painter
        for item in current_canvas.find_withtag("grid"):
            coords = current_canvas.coords(item)
            if len(coords) == 4:  # Only handle rectangle items
                x1, y1, x2, y2 = map(int, coords)
                color = current_canvas.itemcget(item, "fill")
                if color != "white":  # Only draw non-white pixels
                    painter.fillRect(x1, y1, x2 - x1, y2 - y1, QColor(color))

        painter.end()

            # Save the image as a PNG file
        file_name = "layer_output.png"
        image.save(file_name)
        messagebox.showinfo("Save", f"Layer saved as {file_name}")

    def export_as_gif(self):
        """Export all frames as a GIF."""
        if not self.frames:
            messagebox.showinfo("Export", "No frames to export.")
            return

        gif_file = "animation.gif"
        self.frames[0].save(
            gif_file,
            save_all=True,
            append_images=self.frames[1:],
            duration=100,
            loop=0
        )
        messagebox.showinfo("Export", f"Animation saved as {gif_file}")



if __name__ == '__main__':
    Paint()