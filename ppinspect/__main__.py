import os
import sys

from PyQt5 import QtCore, QtGui, QtWidgets, uic

import plyplus


class LoadGrammarThread(QtCore.QThread):
    failed = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(object)

    def __init__(self, filename, parent=None):
        super(LoadGrammarThread, self).__init__(parent)
        self.filename = filename

    def __del__(self):
        self.wait()

    def run(self):
        sys.setrecursionlimit(3000)

        with open(self.filename, 'r') as grammarfile:
            try:
                grammar = plyplus.Grammar(grammarfile)
            except plyplus.GrammarException as e:
                self.failed.emit(str(e))
            else:
                self.done.emit(grammar)


class LoadSourceThread(QtCore.QThread):
    failed = QtCore.pyqtSignal(str)
    done = QtCore.pyqtSignal(object)

    def __init__(self, grammar, filename, parent=None):
        super(LoadSourceThread, self).__init__(parent)
        self.grammar = grammar
        self.filename = filename

    def __del__(self):
        self.wait()

    def run(self):
        with open(self.filename, 'r') as sourcefile:
            source = sourcefile.read()

        try:
            ast = self.grammar.parse(source)
        except plyplus.ParseError as e:
            self.failed.emit(str(e))
        else:
            self.done.emit(ast)


class PPInspectWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super(PPInspectWindow, self).__init__(*args, **kwargs)

        self.grammar = None
        self.ast = None

    @QtCore.pyqtSlot(name="on_filterLineEdit_returnPressed")
    def update_ui(self):
        self.loadSourceAction.setEnabled(self.grammar is not None)
        self.filterLineEdit.setEnabled(self.ast is not None)

        if self.ast is not None:
            model = QtGui.QStandardItemModel(self)
            selector = self.filterLineEdit.text()
            if selector:
                tail = self.ast.select(selector)
            else:
                tail = [self.ast]

            self._append_tail(model, tail)
            self.parseTreeView.setModel(model)

    def _append_tail(self, model, tail):
        for node in tail:
            if plyplus.is_stree(node):
                item = QtGui.QStandardItem(node.head)
                self._append_tail(item, node.tail)
            else:
                item = QtGui.QStandardItem(str(node))
            model.appendRow(item)

    @QtCore.pyqtSlot(name='on_loadGrammarAction_triggered')
    def load_grammar(self):
        # noinspection PyArgumentList
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(parent=self, caption='Open Grammar File')

        if filename:
            self.loadGrammarAction.setEnabled(False)
            self.loadSourceAction.setEnabled(False)
            self.statusBar().showMessage(self.tr('Loading grammar from {0}...').format(filename))
            thread = LoadGrammarThread(filename, self)

            def failed(msg):
                self.grammar = None
                self.loadGrammarAction.setEnabled(True)
                self.update_ui()
                self.statusBar().showMessage(msg)

            def done(grammar):
                self.grammar = grammar
                self.loadGrammarAction.setEnabled(True)
                self.update_ui()
                self.statusBar().showMessage(self.tr('Grammar loaded.'))

            thread.failed.connect(failed)
            thread.done.connect(done)
            thread.start()

    @QtCore.pyqtSlot(name='on_loadSourceAction_triggered')
    def load_source(self):
        # noinspection PyArgumentList
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(parent=self, caption='Open Source File')

        if filename:
            self.loadSourceAction.setEnabled(False)
            self.filterLineEdit.setEnabled(False)
            self.statusBar().showMessage(self.tr('Parsing source from {0}').format(filename))
            thread = LoadSourceThread(self.grammar, filename, self)

            def failed(msg):
                self.ast = None
                self.update_ui()
                self.statusBar().showMessage(msg)

            def done(ast):
                self.ast = ast
                self.update_ui()
                self.statusBar().showMessage(self.tr('Source tree ready.'))

            thread.failed.connect(failed)
            thread.done.connect(done)
            thread.start()


def main():
    app = QtWidgets.QApplication(sys.argv)

    uifile = os.path.join(os.path.dirname(__file__), 'mainwindow.ui')
    win = uic.loadUi(uifile, PPInspectWindow())
    win.update_ui()
    win.show()

    app.exec_()

if __name__ == '__main__':
    main()
