import os
import sys
import logging
import threading
import subprocess
from functools import partial

import appdirs
import yaml

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtCore import pyqtSignal, QObject

__component__ = 'hugo-gui'


class Application(QObject):
    develStatusChanged = pyqtSignal(str)
    publishStatusChanged = pyqtSignal(str)

    def __init__(self):
        super(Application,self).__init__()
        self.config_dir = appdirs.user_config_dir(__component__)
        self.configpath = os.path.join(self.config_dir,'conf.yaml')
        self.config = self._get_config()

    @property
    def basepath(self):
        return self.config.get('basepath','')

    @basepath.setter
    def basepath(self,value):
        self.config['basepath'] = value
        self._persist_config()

    @property
    def publicpath(self):
        return os.path.join(self.config['basepath'],'public')

    @property
    def is_initialized(self):
        return os.path.isfile(self.siteconfig)

    def _get_config(self):
        res = None
        try:
            with open(self.configpath,'r') as f:
                res = yaml.load(f.read())
        except OSError:
            pass
        return res or {}

    def _persist_config(self):
        try:
            with open(self.configpath,'w') as f:
                f.write(yaml.dump(self.config,indent=4))
        except FileNotFoundError:
            os.makedirs(self.config_dir)
            with open(self.configpath,'w') as f:
                f.write(yaml.dump(self.config,indent=4))

    @property
    def siteconfig(self):
        return os.path.join(self.basepath,'config.toml')

    def initialize(self,basepath):
        self.basepath = basepath
        if not os.path.isfile(self.siteconfig):
            subprocess.call(['hugo','new','site','.'],cwd=self.basepath)
        if not os.path.isdir(os.path.join(self.basepath,'.git')):
            subprocess.call(['git','init','.'],cwd=self.basepath)
            subprocess.call(['git','submodule','add','https://github.com/azmelanar/hugo-theme-pixyll.git','themes/pixyll'],cwd=self.basepath)
            with open(self.siteconfig,'a') as conf:
                conf.write('theme = "pixyll"\n')
        return True

    def _watch_devel_server(self):
        for raw in iter(self._hugo_server.stdout.readline,''):
            line = raw.decode('utf-8')
            if line.startswith('Web Server'):
                line = line[line.find('//'):line.rfind('/')]
                self.develStatusChanged.emit(line)

    def start_devel_server(self):
        self._hugo_server = subprocess.Popen(['hugo','server','-D'],cwd=self.basepath,stdout=subprocess.PIPE)
        self._read_thread = threading.Thread(target=self._watch_devel_server)
        self._read_thread.daemon = True
        self._read_thread.start()

    def publish(self):
        subprocess.call(['hugo'],cwd=self.basepath)
        git_status = subprocess.check_output(['git','status'],cwd=self.publicpath).decode('utf-8')
        if 'nothing to commit' not in git_status:
            text,status = QInputDialog.getMultiLineText(self,'Publish Blog','Describe your changes','')
            if status:
                subprocess.call(['git','add','.'],cwd=self.publicpath)
                subprocess.call(['git','commit','.','-m',text],cwd=self.publicpath)
        if 'Your branch is up to date with' not in git_status:
            subprocess.call(['git','push','origin','master'],cwd=self.publicpath)
        res = subprocess.check_output(['git','config','--get','remote.origin.url'],cwd=self.publicpath).decode('utf-8')
        self.publishStatusChanged.emit(res[res.find('/')+1:].strip())

    def edit_post(self,text):
        name = '{0}.md'.format(text)
        path = os.path.join(self.basepath,'content','post',name)
        if not os.path.isfile(path):
            subprocess.call(['hugo','new',os.path.join('post',name)],cwd=self.basepath)
        else:
            self.start_editor(path)

    def start_editor(self,relpath):
        path = os.path.join(self.basepath,relpath)
        if sys.platform.startswith('darwin'):
            subprocess.Popen(['open',path])
        elif os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            subprocess.Popen(['xdg-open',path])

class MainWidget(QWidget):
    DEVEL_STATUS = 'The development blog is at: <a href="http:{0}"><font color=black>{0}</font></a>'
    PUBLISH_STATUS = 'The public blog is reachable at: <a href="https:{0}"><font color=black>{0}</font></a>'

    def __init__(self,app,parent=None):
        super(MainWidget,self).__init__(parent=parent)
        self.app = app
        self._hugo_server = None
        self.resize(250, 150)
        self.move(300, 300)
        self.setWindowTitle('Hugo')
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        if not self.app.is_initialized:
            self.show_init_frame()
        else:
            self.show_normal_frame()

    def show_init_frame(self):
        self._button = QPushButton('Initialize')
        self._button.clicked.connect(self._select_path_init)
        self.layout.addWidget(self._button)

    def show_normal_frame(self):
        self.app.start_devel_server()
        self.basepath_label = QLabel('Basepath is: %s'%self.app.basepath)
        self.layout.addWidget(self.basepath_label)
        button = QPushButton('New Post')
        button.clicked.connect(self.make_new_post)
        self.layout.addWidget(button)
        button = QPushButton('Publish')
        button.clicked.connect(self.app.publish)
        self.layout.addWidget(button)
        button = QPushButton('Publish')
        devel_status = QLabel(self)
        devel_status.setOpenExternalLinks(True)
        self.layout.addWidget(devel_status)
        self.app.develStatusChanged.connect(partial(self.set_status,devel_status,self.DEVEL_STATUS))
        publish_status = QLabel(self)
        publish_status.setOpenExternalLinks(True)
        self.layout.addWidget(publish_status)
        self.app.publishStatusChanged.connect(partial(self.set_status,publish_status,self.PUBLISH_STATUS))

    def set_status(self,label,templ,text):
        label.setText(templ.format(text))

    def make_new_post(self):
        text,status = QInputDialog.getText(self,'New Blog Post','Post Title', QLineEdit.Normal,'')
        if status:
            self.app.edit_post(text)

    def _select_path_init(self):
        res = str(QFileDialog.getExistingDirectory(self, "Hugo")).strip()
        if os.path.isdir(res):
            if self.app.initialize(res):
                self._button.deleteLater()
                self.show_normal_frame()

    def on_close(self):
        if self._hugo_server is not None:
            self._hugo_server.kill()


def main():
    dirpath = os.path.dirname(__file__)
    qt_app = QApplication.instance()
    if qt_app is None:
        qt_app = QApplication([])
    win = QMainWindow()
    win.setWindowIcon(QIcon('icon.png'))
    app = Application()
    # app.config.pop('basepath',None)
    w = MainWidget(app,win)
    win.setCentralWidget(w)
    win.show()
    sys.exit(qt_app.exec_())

if __name__ == '__main__':
    main()

