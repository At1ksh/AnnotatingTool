import sys
import os
import zipfile
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QFileDialog,
    QVBoxLayout, QWidget, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
    QComboBox, QHBoxLayout, QListWidget, QListWidgetItem, QScrollArea,
    QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QStyleFactory
)
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QPointF
import cv2
import numpy as np

class SettingsDialog(QDialog):
    def __init__(self,current_classes, current_export_dir="",parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings⚙️")
        self.setFixedSize(450, 250)
        
        self.update_classes=current_classes.copy()
        self.export_dir=current_export_dir
        
        
        layout=QVBoxLayout()
        tabs=QTabWidget()
        
        
        #Pehla tab
        class_tab=QWidget()
        class_layout=QVBoxLayout()
        class_layout.addWidget(QLabel("Add class names, separated by commas:"))  
        self.class_input = QLineEdit()
        self.class_input.setText(",".join(current_classes))
        class_layout.addWidget(self.class_input)
        class_tab.setLayout(class_layout)
        
        #Doosra tab
        advanced_tab=QWidget()
        advanced_layout=QVBoxLayout()
        advanced_layout.addWidget(QLabel("Select directory to store images and labels:"))
        
        self.export_path_input = QLineEdit()
        self.export_path_input.setText(current_export_dir)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.choose_export_folder)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.export_path_input)
        path_layout.addWidget(browse_button)
        
        advanced_layout.addLayout(path_layout)
        advanced_tab.setLayout(advanced_layout)
        
        tabs.addTab(class_tab,"Classes")
        tabs.addTab(advanced_tab,"Advanced")
        
        layout.addWidget(tabs)
        
        #Ok/Caneceeceellll boootn
        button_layout=QHBoxLayout()
        ok_button=QPushButton("OK")
        cancel_button=QPushButton("Cancel")
        ok_button.clicked.connect(self.accept) 
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
              
        #self.class_input=QLineEdit()
        #self.class_input.setText(",".join(current_classes))
        #layout.addWidget(self.class_input)

        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def get_updated_classes(self):
        text=self.class_input.text()
        classes=[c.strip() for c in text.split(",") if c.strip()]
        return classes
    
    def choose_export_folder(self):
        folder=QFileDialog.getExistingDirectory(self, "Select Export Directory")
        if folder:
            self.export_path_input.setText(folder)
    
    def get_export_directory(self):
        return self.export_path_input.text().strip()
    
class Annotator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FAP: Fully Automated Production Annotator")
        self.setGeometry(100, 100, 1000, 700)
        self.showMaximized()
        self.unsaved_changes=False

        self.class_names=["Autobiography","HSE"]
        self.image = None
        self.points = []
        self.class_name = ""
        self.image_dir=""
        self.image_list=[]
        self.annotations=[]
        self.current_points=[]
        self.export_dir=""

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        
        ##left side stuffs
        left_layout = QVBoxLayout()

        # Class selector
        self.class_dropdown = QComboBox()
        self.class_dropdown.addItems(self.class_names)
        self.class_dropdown.currentIndexChanged.connect(self.update_active_class_label)# Add your classes here
        self.active_class_label=QLabel()
        self.update_active_class_label()
        
        
        # Buttons
        load_folder_button = QPushButton("Load Folder")
        save_button = QPushButton("Save Annotation")
        clear_button = QPushButton("Clear Points")
        preview_button = QPushButton("Preview Annotation")
        reset_button = QPushButton("Reset Annotation(s)")
        settings_button = QPushButton("Settings⚙️")
        export_button = QPushButton("📦 Export to ZIP")
        mark_empty_button=QPushButton("Mark as Empty")
        
        

        load_folder_button.clicked.connect(self.load_folder)
        save_button.clicked.connect(self.save_annotation)
        clear_button.clicked.connect(self.clear_points)
        preview_button.clicked.connect(self.preview_annotation)
        reset_button.clicked.connect(self.reset_annotations)
        settings_button.clicked.connect(self.open_settings)
        export_button.clicked.connect(self.export_to_zip)
        mark_empty_button.clicked.connect(self.mark_image_as_empty)
        

        button_layout = QHBoxLayout()
        button_layout.addWidget(load_folder_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(mark_empty_button)
        button_layout.addWidget(clear_button)
        button_layout.addWidget(self.active_class_label)
        button_layout.addWidget(self.class_dropdown)
        button_layout.addWidget(preview_button)
        button_layout.addWidget(reset_button)
        button_layout.addWidget(settings_button)


        # Image display
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Top-center alignment
        self.image_label.setScaledContents(False)  # Do NOT auto-rescale
        self.image_label.mousePressEvent = self.get_mouse_position

        #main_layout.addLayout(button_layout)
        #main_layout.addWidget(self.image_label)
        #main_layout.addWidget(self.status_label)
        
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        

        
        #left side thingers
        left_layout.addLayout(button_layout)
        left_layout.addWidget(self.image_label)
        left_layout.addWidget(self.status_label) 
        left_layout.addWidget(export_button)   
        
        #right side thinger
        self.image_list_widget=QListWidget()
        self.image_list_widget.itemClicked.connect(self.image_selected)
        
        #Mix them up
        main_layout.addLayout(left_layout,4)
        main_layout.addWidget(self.image_list_widget, 1)
        

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        

    def show_status(self, message, success=False):
        color = "green" if success else "red"
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.status_label.setText(message)
        
        
    def preview_annotation(self):
        if len(self.points) != 4:
            self.status_label.setText("❌ Please select exactly 4 points to preview.")
            #print("❌ Please select exactly 4 points to preview.")
            return

        if self.image is None:
            self.status_label.setText("❌ No image loaded to preview.")
            #print("❌ No image loaded.")
            return

        img_copy = self.image.copy()

        # Draw polygon
        pts = np.array(self.points, np.int32).reshape((-1, 1, 2))
        cv2.polylines(img_copy, [pts], isClosed=True, color=(0, 255, 0), thickness=2)

        # Draw point numbers
        for idx, (x, y) in enumerate(self.points):
            cv2.circle(img_copy, (x, y), 5, (0, 0, 255), -1)
            cv2.putText(img_copy, str(idx + 1), (x + 5, y - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        height, width, channel = img_copy.shape
        bytes_per_line = channel * width
        q_img = QImage(img_copy.data, width, height, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)

        self.image_label.setPixmap(pixmap)
        self.image_label.setFixedSize(pixmap.size())

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.image_path = file_path
            img = cv2.imread(file_path)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            # Resize to 1280x720
            img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA)
            self.image = img
            self.display_image()
            self.points = []

    def display_image(self):
        if self.image is not None:
            img_copy = self.image.copy()
            
            for ann in self.annotations:
                pts=np.array(ann["points"],np.int32).reshape((-1,1,2))
                cv2.polylines(img_copy,[pts],isClosed=True,color=(0,255,0),thickness=2)
                
                for(x,y) in ann["points"]:
                    cv2.circle(img_copy,(x,y),5,(0,0,255),-1)
                    
                class_name=ann["class"]
                class_index = self.class_names.index(class_name) if class_name in self.class_names else "?"
                label=f"{class_name} ({class_index})"
                x_text,y_text=ann["points"][0]
                cv2.putText(
                    img_copy, label, (x_text+5,y_text-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,0),2, cv2.LINE_AA
                )
            
            #for idx, ann in enumerate(self.annotations):
            #    pts=np.array(ann["points"], np.int32).reshape((-1, 1, 2))
            #    cv2.polylines(img_copy, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
            #    for i,(x,y) in enumerate(ann["points"]):
            #        cv2.circle(img_copy, (x, y), 5, (255,0,0), -1)
            
            for(x,y) in self.current_points:
                cv2.circle(img_copy, (x, y), 5, (255,0,0), -1)
                

            height, width, channel = img_copy.shape
            bytes_per_line = channel * width
            q_img = QImage(img_copy.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_img)
            self.image_label.setPixmap(pixmap)
    
            #self.image_label.setFixedSize(pixmap.size())  # Force QLabel to match image size


    def load_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if not folder:
            return

        self.image_dir = folder
        self.image_list = sorted([
            f for f in os.listdir(folder)
            if f.lower().endswith(('.jpg', '.png', '.jpeg'))
        ])

        self.image_list_widget.clear()
        for img_name in self.image_list:
            item = QListWidgetItem(img_name)
            self.image_list_widget.addItem(item)

        self.show_status(f"📁 Loaded {len(self.image_list)} images from folder.", success=True)

        # Load first image by default
        if self.image_list:
            self.load_image_by_name(self.image_list[0])

    def get_mouse_position(self, event):
        if self.image is None:
            return
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return
        
        pixmap_width=pixmap.width()
        pixmap_height=pixmap.height()
        label_width=self.image_label.width()
        label_height=self.image_label.height()
        
        x_offset= max((label_width - pixmap_width) // 2, 0)
        y_offset= max((label_height - pixmap_height) // 2, 0)   

        x = event.pos().x() - x_offset
        y = event.pos().y() - y_offset
        
        # Ensure click is within image bounds
        if x < 0 or y < 0 or x >= pixmap_width or y >= pixmap_height:
            return
        
        img_height, img_width, _ = self.image.shape
        img_x=int(x * img_width / pixmap_width)
        img_y=int(y * img_height / pixmap_height)
        
        self.current_points.append((img_x, img_y))
        
        if(len(self.current_points) == 4):
            class_index = self.class_dropdown.currentIndex()
            class_name=self.class_dropdown.currentText()
            self.annotations.append({
                "class": class_name,
                "points": self.current_points.copy()
            })
            self.current_points = []
            self.show_status(f"✅ Annotation added for class {class_name} #{len(self.annotations)}", success=True)

        #self.points.append((int(x), int(y)))
        self.display_image()
        self.unsaved_changes = True


    def load_image_by_name(self, filename):
        file_path = os.path.join(self.image_dir, filename)
        self.image_path = file_path
        self.annotations = []
        self.current_points=[]

        img = cv2.imread(file_path)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_AREA)
        self.image = img
        #self.display_image()

        # Try to load existing annotation
        label_path = os.path.splitext(file_path)[0] + ".txt"
        if os.path.exists(label_path):
            with open(label_path, "r") as f:
                for line in f:
                    parts=line.strip().split()
                    if(len(parts)==9):
                        try:
                            class_id=int(parts[0])
                            if 0 <= class_id < len(self.class_names):
                                class_name=self.class_names[class_id]
                                coords=list(map(int,parts[1:]))
                                points=[(coords[i],coords[i+1]) for i in range(0,8,2)]
                                self.annotations.append({
                                    "class":class_name,
                                    "points":points
                                })
                            else:
                                self.show_status(f"❌ Invalid class ID {class_id} in annotation file.", success=False)
                        except ValueError:
                            self.show_status("❌ Error parsing annotation file. Please check format.", success=False)
                #line = f.readline().strip().split()
                #if len(line) == 9:
                    #coords = list(map(int, line[1:]))
                    #self.points = [(coords[i], coords[i + 1]) for i in range(0, 8, 2)]
        self.display_image()

    def save_annotation(self):    
        if not self.export_dir:
            self.show_status("❌ Export directory not set. Please configure in settings.")
            return

        if not self.image_path:
            self.show_status("❌ No image loaded")
            return
        
        images_dir=os.path.join(self.export_dir,"images")
        labels_dir=os.path.join(self.export_dir,"labels")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        
        image_filename=os.path.basename(self.image_path)
        image_save_path=os.path.join(images_dir,image_filename)    
        label_filename=os.path.splitext(image_filename)[0]+".txt"
        label_save_path=os.path.join(labels_dir,label_filename)
        
        resized_img_bgr=cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)  # Convert back to BGR for OpenCV saving
        cv2.imwrite(image_save_path, resized_img_bgr)
        
        with open(label_save_path,"w")as f:
            for ann in self.annotations:
                class_name=ann["class"]
                try:
                    class_index=self.class_names.index(class_name)
                except ValueError:
                    self.show_status(f"❌ Class '{class_name}' not found in class list.")
                    return
                coords=" ".join([f"{x} {y}" for x, y in ann["points"]])
                f.write(f"{class_index} {coords}\n")
        
        self.unsaved_changes=False
        
        if self.annotations:
            self.show_status(f"✅ Saved {len(self.annotations)} annotation(s) to {label_save_path}", success=True)

        else:
            self.show_status(f"🟡 No annotations found. Saved empty label file to {label_save_path}", success=True)
        # Save annotation
        #label_path = os.path.splitext(self.image_path)[0] + ".txt"
        
        #with open(label_path, "w") as f:
        #    for ann in self.annotations:
        #        coords=" ".join([f"{x} {y}" for x, y in ann["points"]])
        #        f.write(f"{ann['class']} {coords}\n")
        #        
        #    class_index = self.class_dropdown.currentIndex()
        #    flat_coords = " ".join([f"{x} {y}" for x, y in self.points])
        #    f.write(f"{class_index} {flat_coords}\n")
        #self.status_label.setText(f"✅ Annotation saved to {label_path}")
        #print(f"✅ Saved annotation to {label_path}")

        # Save the resized image (1280x720) to same location, overwrite original
        #image_save_path = self.image_path
        #resized_img_bgr = cv2.cvtColor(self.image, cv2.COLOR_RGB2BGR)  # Convert back to BGR for OpenCV saving
        #cv2.imwrite(image_save_path, resized_img_bgr)
        #self.status_label.setText(f"✅ Saved {len(self.annotations)} annotation(s) to file.", success=True)
        #print(f"📸 Resized image saved to {image_save_path}")


    def clear_points(self):
        if self.current_points:
            self.current_points=[]
            self.show_status("Cleared in progress points")
        elif self.annotations:
            removed=self.annotations.pop()
            class_index=removed['class']
            class_name=self.class_dropdown.itemText(class_index)
            self.show_status(
                f"🗑️ Removed annotation for class {class_name} ({class_index}) #{len(self.annotations) + 1}",
                success=True
            )
        else:
            self.show_status("Nothing to clear.")
        #self.points = []
        self.display_image()
        self.unsaved_changes = True

    def image_selected(self, item):
        if self.unsaved_changes:
            reply = QMessageBox.question(self,'Unsaved Annotations','You have unsaved annotations. Do you want to continue without saving?',QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                return
        image_name = item.text()
        self.load_image_by_name(image_name)
        self.unsaved_changes=False
        
    def reset_annotations(self):
        self.annotations=[]
        self.current_points=[]
        self.display_image()
        self.unsaved_changes = True
        self.show_status("🧹 Cleared all annotations for this image.")
        
    def update_active_class_label(self):
        index=self.class_dropdown.currentIndex()
        name=self.class_dropdown.currentText()
        self.active_class_label.setText(f"Class: {name} ({index})")
        
    def open_settings(self):
        dialog=SettingsDialog(self.class_names, self.export_dir, self)
        if dialog.exec_():
            new_classes=dialog.get_updated_classes()
            if new_classes:
                self.class_names=new_classes
                self.class_dropdown.clear()
                self.class_dropdown.addItems(new_classes)
                self.update_active_class_label()
                self.show_status(f"Class list updated: {', '.join(new_classes)}", success=True)
            else:
                self.show_status("⚠️ No classes provided. Class list not updated.")
            
            new_export_dir=dialog.get_export_directory()
            if new_export_dir:
                self.export_dir=new_export_dir
                self.show_status(f"📁 Export directory set to: {self.export_dir}")
    
    def export_to_zip(self):
        if not self.export_dir or not self.class_names:
            self.show_status("❌ Export directory or class names not set. Please configure in settings.")
            return
        
        images_dir = os.path.join(self.export_dir, "images")
        labels_dir = os.path.join(self.export_dir, "labels")
        os.makedirs(images_dir, exist_ok=True)
        os.makedirs(labels_dir, exist_ok=True)
        
        #clasese.txt ka kam
        classes_path=os.path.join(self.export_dir,"classes.txt")
        with open(classes_path,"w") as f:
            f.write("\n".join(self.class_names))
        
        zip_path,_=QFileDialog.getSaveFileName(self,"SAVE ZIP File","Zip Files (*.zip)")
        if not zip_path:
            self.show_status("❌ Export cancelled.")
            return
        
        try:
            with zipfile.ZipFile(zip_path,'w',zipfile.ZIP_DEFLATED) as zipf:
                for folder_name in ['images','labels']:
                    folder_path=os.path.join(self.export_dir,folder_name)
                    for root, _,files in os.walk(folder_path):
                        for file in files:
                            full_path=os.path.join(root, file)
                            rel_path=os.path.relpath(full_path,self.export_dir)
                            zipf.write(full_path,arcname=rel_path)
                            
                zipf.write(classes_path,arcname="classes.txt")
            
            self.show_status(f"✅ Exported dataset to {zip_path}", success=True)
        
        except Exception as e:
            self.show_status(f"❌ Export failed: {str(e)}", success=False)

    def mark_image_as_empty(self):
        if not self.image_path:
            self.show_status("❌ No image loaded.", success=False)
            return
        
        self.annotations=[]
        self.current_points=[]
        
        label_path=os.path.splitext(self.image_path)[0]+".txt"
        with open(label_path,"w") as f:
            pass
        
        if self.export_dir:
            os.makedirs(os.path.join(self.export_dir,"labels"),exist_ok=True)
            export_label_path=os.path.join(self.export_dir,"labels",os.path.basename(label_path))
            with open(export_label_path, "w")as f:
                pass
            
        self.show_status("🟡 Marked image as empty and saved label file.", success=True)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = Annotator()
    window.show()
    sys.exit(app.exec_())


