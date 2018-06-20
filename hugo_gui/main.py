import os
import sys
import appdirs
import logging

import yaml
import sh

from PyQt5.QtWidgets import QApplication, QWidget, QFileDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog
from PyQt5.QtCore import pyqtSignal

from . import __component__

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
        sh.hugo(_cwd=self.basepath)
        git_status = sh.git.status(_cwd=self.publicpath)
        if 'nothing to commit' not in git_status:
            text,status = QInputDialog.getMultiLineText(self,'Publish Blog','Describe your changes','')
            if status:
                sh.git.add('.',_cwd=self.publicpath)
                sh.git.commit('.','-m',text,_cwd=self.publicpath)
        if 'Your branch is up to date with' not in git_status:
            sh.git.push('origin','master',_cwd=self.publicpath)
        res = str(sh.git.config('--get','remote.origin.url',_cwd=self.publicpath))
        self.publishStatusChanged.emit(self.PUBLISH_STATUS.format(res[res.find('/')+1:].strip()))

    def process_output(self,line):
        if line.startswith('Web Server'):
            line = line[line.find('//'):line.rfind('/')]
            self.develStatusChanged.emit(self.DEVEL_STATUS.format(line))

    def start_devel_server(self):
        self._hugo_server = sh.hugo.server('-D',_cwd=self.basepath,_bg=True,_out=self.process_output)

    def start_editor(self,relpath):
        path = os.path.join(self.basepath,relpath)
        if sys.platform.startswith('darwin'):
            sh.open(path)
        elif os.name == 'nt':
            os.startfile(path)
        elif os.name == 'posix':
            sh.xdg_open(path)

    def make_new_post(self):
        text,status = QInputDialog.getText(self,'New Blog Post','Post Title', QLineEdit.Normal,'')
        if status:
            rel_name = 'post/{0}.md'.format(text)
            try:
                sh.hugo.new(rel_name,_cwd=self.basepath)
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
            self._select_path_init()

    def _select_path_init(self):
        self.config['basepath'] = basepath = str(QFileDialog.getExistingDirectory(self, "Hugo"))
        self.siteconfig = os.path.join(basepath,'config.toml')
        if not os.path.isfile(self.siteconfig):
            sh.hugo.new.site('.',_cwd=basepath)
        if not os.path.isdir(os.path.join(basepath,'.git')):
            sh.git.init('.',_cwd=basepath)
            sh.git.submodule.add('https://github.com/azmelanar/hugo-theme-pixyll.git','themes/pixyll',_cwd=basepath)
            with open(self.siteconfig,'a') as conf:
                conf.write('theme = "pixyll"\n')
        self._persist_config()

    def closeEvent(self,event):
        if self._hugo_server is not None:
            self._hugo_server.kill()
        event.accept()
        

def main():
    app = QApplication(sys.argv)
    w = MainWidget()
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
    
