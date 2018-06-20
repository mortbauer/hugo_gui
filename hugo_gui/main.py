import os
import sys
import appdirs
import logging
import subprocess

import yaml

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QMainWindow, QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtCore import pyqtSignal

from hugo_gui import __component__


class MainWidget(QWidget):

    develStatusChanged = pyqtSignal(str)
    publishStatusChanged = pyqtSignal(str)
    DEVEL_STATUS = 'The development blog is at: <a href="http:{0}"><font color=black>{0}</font></a>'
    PUBLISH_STATUS = 'The public blog is reachable at: <a href="https:{0}"><font color=black>{0}</font></a>'

    def __init__(self,parent=None):
        super(MainWidget,self).__init__(parent=parent)
        self._hugo_server = None
        self.resize(250, 150)
        self.move(300, 300)
        self.setWindowTitle('Hugo')
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.config_dir = appdirs.user_config_dir(__component__)
        self.configpath = os.path.join(self.config_dir,'conf.yaml')
        self.config = self._get_config()

    def start(self):
        if 'basepath' not in self.config or not os.path.isdir(self.basepath):
            self._show_init()
        self.start_devel_server()
        self.basepath_label = QLabel('Basepath is: %s'%self.config['basepath'])
        self.layout.addWidget(self.basepath_label)
        button = QPushButton('New Post')
        button.clicked.connect(self.make_new_post)
        self.layout.addWidget(button)
        button = QPushButton('Publish')
        button.clicked.connect(self.publish)
        self.layout.addWidget(button)
        button = QPushButton('Publish')
        devel_status = QLabel(self)
        devel_status.setOpenExternalLinks(True)
        self.layout.addWidget(devel_status)
        self.develStatusChanged.connect(devel_status.setText)
        publish_status = QLabel(self)
        publish_status.setOpenExternalLinks(True)
        self.layout.addWidget(publish_status)
        self.publishStatusChanged.connect(publish_status.setText)

    @property
    def basepath(self):
        return self.config['basepath']

    @property
    def publicpath(self):
        return os.path.join(self.config['basepath'],'public')

    def publish(self):
        subprocess.call(['hugo'],cwd=self.basepath)
        git_status = subprocess.check_output(['git','status'],cwd=self.publicpath)
        if 'nothing to commit' not in git_status:
            text,status = QInputDialog.getMultiLineText(self,'Publish Blog','Describe your changes','')
            if status:
                subprocess.call(['git','add','.'],cwd=self.publicpath)
                subprocess.call(['git','commit','.','-m',text],cwd=self.publicpath)
        if 'Your branch is up to date with' not in git_status:
            subprocess.call(['git','push','origin','master'],cwd=self.publicpath)
        res = str(subprocess.check_output(['git','config','--get','remote.origin.url'],cwd=self.publicpath))
        self.publishStatusChanged.emit(self.PUBLISH_STATUS.format(res[res.find('/')+1:].strip()))

    def _watch_devel_server(self):
        for line in iter(self._hugo_server.stdout.readline,''):
            if line.startswith('Web Server'):
                line = line[line.find('//'):line.rfind('/')]
                self.develStatusChanged.emit(self.DEVEL_STATUS.format(line))

    def start_devel_server(self):
        self._hugo_server = subprocess.Popen(['hugo','server','-D'],cwd=self.basepath,stdout=subprocess.PIPE)
        self._read_thread = threading.Thread(target=self._watch_devel_server)
        self._read_thread.daemon = True
        self._read_thread.start()

    def start_editor(self,relpath):
        path = os.path.join(self.basepath,relpath)
        if sys.platform.startswith('darwin'):
            subprocess.Popen(['open',path])
        elif os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            subprocess.Popen(['xdg_open',path])

    def make_new_post(self):
        text,status = QInputDialog.getText(self,'New Blog Post','Post Title', QLineEdit.Normal,'')
        if status:
            rel_name = 'post/{0}.md'.format(text)
            try:
                subprocess.call(['hugo','new',rel_name],cwd=self.basepath)
            except:
                self.start_editor(os.path.join('content',rel_name))

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


    def _show_init(self):
        msg = QMessageBox(self)
        msg.setText('Seems like nothing configured there yet.')
        # button.clicked.connect('
        msg.setInformativeText('Do you want to start a new blog?')
        msg.setStandardButtons(QMessageBox.Ok)
        res = msg.exec()
        if res == QMessageBox.Ok:
            print('!!!!!!!')
            self._select_path_init()

    def _select_path_init(self):
        self.config['basepath'] = basepath = str(QFileDialog.getExistingDirectory(self, "Hugo"))
        self.siteconfig = os.path.join(basepath,'config.toml')
        if not os.path.isfile(self.siteconfig):
            subprocess.call(['hugo','new','site','.'],cwd=basepath)
        if not os.path.isdir(os.path.join(basepath,'.git')):
            subprocess.call(['git','init','.'],cwd=basepath)
            subprocess.call(['git','submodule','add','https://github.com/azmelanar/hugo-theme-pixyll.git','themes/pixyll'],cwd=basepath)
            with open(self.siteconfig,'a') as conf:
                conf.write('theme = "pixyll"\n')
        self._persist_config()

    def closeEvent(self,event):
        print('got close')
        if self._hugo_server is not None:
            self._hugo_server.kill()
        event.accept()


def main():
    dirpath = os.path.dirname(__file__)
    app = QApplication(sys.argv)
    win = QMainWindow()
    print(os.path.join(dirpath,'hugo.png'))
    win.setWindowIcon(QIcon(os.path.join(dirpath,'hugo_1.png')))
    w = MainWidget(win)
    win.setCentralWidget(w)
    w.start()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

