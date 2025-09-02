# dns_subdomain_gui.py
import sys
import threading
import queue
import requests
import dns.resolver

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QProgressBar, QFileDialog,
    QMessageBox, QSpinBox, QCheckBox, QHeaderView, QGroupBox, QGridLayout, QComboBox
)

LIGHT_QSS = """
* { font-family: 'Segoe UI', sans-serif; }
QWidget { background: #f7f7fb; color: #202124; }
QLineEdit, QSpinBox, QTableWidget, QGroupBox { background: white; border: 1px solid #d0d3d8; border-radius: 8px; padding: 6px; }
QPushButton { background: #1a73e8; color: white; border: none; padding: 8px 12px; border-radius: 10px; }
QPushButton:hover { background: #1669c1; }
QPushButton:disabled { background: #9bb7e6; }
QProgressBar { background: #e6e8ee; border-radius: 8px; text-align: center; }
QProgressBar::chunk { background: #1a73e8; border-radius: 8px; }
QGroupBox { border: 1px solid #d0d3d8; margin-top: 10px; padding-top: 12px; }
QHeaderView::section { background: #eef1f6; padding: 6px; border: none; }
"""

DARK_QSS = """
* { font-family: 'Segoe UI', sans-serif; }
QWidget { background: #0f1218; color: #e6e8ee; }
QLineEdit, QSpinBox, QTableWidget, QGroupBox { background: #171b22; border: 1px solid #2a2f3a; border-radius: 8px; padding: 6px; color: #e6e8ee; }
QPushButton { background: #3b82f6; color: white; border: none; padding: 8px 12px; border-radius: 10px; }
QPushButton:hover { background: #2563eb; }
QPushButton:disabled { background: #27344d; }
QProgressBar { background: #151923; border-radius: 8px; text-align: center; color: #e6e8ee; }
QProgressBar::chunk { background: #3b82f6; border-radius: 8px; }
QGroupBox { border: 1px solid #2a2f3a; margin-top: 10px; padding-top: 12px; }
QHeaderView::section { background: #0f141c; padding: 6px; border: none; }
"""


class DNSWorker(QObject):
    progress = pyqtSignal(int, int)
    dns_record = pyqtSignal(str, str, str)  # host, rtype, answer_text
    subdomain_hit = pyqtSignal(str, str)    # subdomain, url
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, domain: str, rtypes: list, wordlist_path: str, max_threads: int):
        super().__init__()
        self.domain = domain
        self.rtypes = rtypes
        self.wordlist_path = wordlist_path
        self.max_threads = max_threads
        self._stop = False

    def stop(self):
        self._stop = True

    def _resolve_once(self, host: str):
        # Emit DNS records found for selected types
        for rtype in self.rtypes:
            if self._stop:
                return
            try:
                answers = dns.resolver.resolve(host, rtype, lifetime=3)
                for r in answers:
                    self.dns_record.emit(host, rtype, str(r.to_text()))
            except Exception:
                # ignore missing records; continue
                pass

    def _check_subdomain(self, sub: str):
        full_host = f"{sub}.{self.domain}"
        exists = False
        # quick existence check
        for rtype in self.rtypes or ["A"]:
            try:
                dns.resolver.resolve(full_host, rtype, lifetime=2)
                exists = True
                break
            except Exception:
                continue
        if not exists:
            return

        # try https then http
        for scheme in ("https", "http"):
            if self._stop:
                return
            url = f"{scheme}://{full_host}"
            try:
                r = requests.get(url, timeout=3)
                if r.status_code < 400:
                    self.subdomain_hit.emit(full_host, url)
                    return
            except requests.RequestException:
                continue

    def run(self):
        if not self.domain:
            self.error.emit("Domain is required.")
            self.finished.emit()
            return

        # initial DNS of domain itself
        try:
            self._resolve_once(self.domain)
        except Exception:
            pass

        # subdomain phase
        subs = []
        total = 0
        if self.wordlist_path:
            try:
                with open(self.wordlist_path, "r", encoding="utf-8", errors="ignore") as f:
                    subs = [line.strip() for line in f if line.strip()]
            except Exception as e:
                self.error.emit(f"Failed to read wordlist: {e}")
                self.finished.emit()
                return

        total = len(subs)
        if total == 0:
            # Only DNS phase, mark done
            self.progress.emit(1, 1)
            self.finished.emit()
            return

        q = queue.Queue()
        for s in subs:
            q.put(s)

        def worker():
            while not q.empty() and not self._stop:
                sub = q.get()
                try:
                    self._check_subdomain(sub)
                finally:
                    done = total - q.qsize()
                    self.progress.emit(done, total)
                    q.task_done()

        threads = []
        for _ in range(max(1, self.max_threads)):
            t = threading.Thread(target=worker, daemon=True)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.finished.emit()


class DNSApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DNS + Subdomain Enumeration — GUI")
        self.thread = None
        self.worker = None
        self._dark = True
        self._build_ui()
        self._apply_theme()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Controls
        box = QGroupBox("Target & Options")
        grid = QGridLayout(box)

        self.domain_edit = QLineEdit()
        self.domain_edit.setPlaceholderText("e.g., example.com")

        # Record types
        self.chk_a = QCheckBox("A")
        self.chk_aaaa = QCheckBox("AAAA")
        self.chk_cname = QCheckBox("CNAME")
        self.chk_mx = QCheckBox("MX")
        self.chk_txt = QCheckBox("TXT")
        self.chk_a.setChecked(True)
        self.chk_cname.setChecked(True)
        self.chk_mx.setChecked(True)
        self.chk_txt.setChecked(True)

        self.wordlist_path = QLineEdit()
        self.wordlist_path.setPlaceholderText("subdomains wordlist file...")
        self.browse_btn = QPushButton("Browse")

        self.threads_spin = QSpinBox()
        self.threads_spin.setRange(1, 200)
        self.threads_spin.setValue(20)

        self.theme_toggle = QComboBox()
        self.theme_toggle.addItems(["Dark", "Light"])
        self.theme_toggle.currentIndexChanged.connect(self._toggle_theme)

        grid.addWidget(QLabel("Domain"), 0, 0)
        grid.addWidget(self.domain_edit, 0, 1, 1, 3)
        grid.addWidget(QLabel("Record Types"), 1, 0)
        recs = QHBoxLayout()
        for w in (self.chk_a, self.chk_aaaa, self.chk_cname, self.chk_mx, self.chk_txt):
            recs.addWidget(w)
        grid.addLayout(recs, 1, 1, 1, 3)

        grid.addWidget(QLabel("Wordlist"), 2, 0)
        grid.addWidget(self.wordlist_path, 2, 1, 1, 2)
        grid.addWidget(self.browse_btn, 2, 3)

        grid.addWidget(QLabel("Threads"), 3, 0)
        grid.addWidget(self.threads_spin, 3, 1)
        grid.addWidget(QLabel("Theme"), 3, 2)
        grid.addWidget(self.theme_toggle, 3, 3)

        layout.addWidget(box)

        # Buttons
        btns = QHBoxLayout()
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        layout.addLayout(btns)

        # Tables
        self.dns_table = QTableWidget(0, 3)
        self.dns_table.setHorizontalHeaderLabels(["Host", "Type", "Answer"])
        self.dns_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.dns_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.dns_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        self.sub_table = QTableWidget(0, 2)
        self.sub_table.setHorizontalHeaderLabels(["Subdomain", "URL"])
        self.sub_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.sub_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

        layout.addWidget(QLabel("DNS Records"))
        layout.addWidget(self.dns_table)
        layout.addWidget(QLabel("Discovered Subdomains"))
        layout.addWidget(self.sub_table)

        # Progress / Export
        bottom = QHBoxLayout()
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.export_btn = QPushButton("Export Results")
        self.export_btn.setEnabled(False)
        bottom.addWidget(self.progress, 1)
        bottom.addWidget(self.export_btn)
        layout.addLayout(bottom)

        # Hooks
        self.browse_btn.clicked.connect(self._browse_wordlist)
        self.start_btn.clicked.connect(self._start)
        self.stop_btn.clicked.connect(self._stop)
        self.export_btn.clicked.connect(self._export)

    def _toggle_theme(self):
        self._dark = (self.theme_toggle.currentText() == "Dark")
        self._apply_theme()

    def _apply_theme(self):
        self.setStyleSheet(DARK_QSS if self._dark else LIGHT_QSS)

    def _browse_wordlist(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select wordlist", "", "Text Files (*.txt);;All Files (*)")
        if path:
            self.wordlist_path.setText(path)

    def _selected_rtypes(self):
        r = []
        if self.chk_a.isChecked(): r.append("A")
        if self.chk_aaaa.isChecked(): r.append("AAAA")
        if self.chk_cname.isChecked(): r.append("CNAME")
        if self.chk_mx.isChecked(): r.append("MX")
        if self.chk_txt.isChecked(): r.append("TXT")
        return r

    def _start(self):
        domain = self.domain_edit.text().strip()
        if not domain:
            QMessageBox.warning(self, "Validation", "Enter a domain (e.g., example.com)")
            return

        # reset UI
        self.dns_table.setRowCount(0)
        self.sub_table.setRowCount(0)
        self.progress.setValue(0)
        self.export_btn.setEnabled(False)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        self.thread = QThread()
        self.worker = DNSWorker(
            domain=domain,
            rtypes=self._selected_rtypes(),
            wordlist_path=self.wordlist_path.text().strip(),
            max_threads=self.threads_spin.value(),
        )
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self._on_progress)
        self.worker.dns_record.connect(self._on_dns_record)
        self.worker.subdomain_hit.connect(self._on_sub_hit)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def _stop(self):
        if self.worker:
            self.worker.stop()

    def _on_progress(self, done, total):
        self.progress.setMaximum(100)
        pct = int((done / max(1, total)) * 100)
        self.progress.setValue(pct)

    def _on_dns_record(self, host, rtype, answer):
        r = self.dns_table.rowCount()
        self.dns_table.insertRow(r)
        self.dns_table.setItem(r, 0, QTableWidgetItem(host))
        self.dns_table.setItem(r, 1, QTableWidgetItem(rtype))
        self.dns_table.setItem(r, 2, QTableWidgetItem(answer))
        self.export_btn.setEnabled(True)

    def _on_sub_hit(self, sub, url):
        r = self.sub_table.rowCount()
        self.sub_table.insertRow(r)
        self.sub_table.setItem(r, 0, QTableWidgetItem(sub))
        self.sub_table.setItem(r, 1, QTableWidgetItem(url))
        self.export_btn.setEnabled(True)

    def _on_error(self, msg):
        QMessageBox.critical(self, "Error", msg)

    def _on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        if self.thread:
            self.thread.quit()
            self.thread.wait()

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Results", "dns_subdomains.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("== DNS Records ==\n")
                f.write("Host,Type,Answer\n")
                for r in range(self.dns_table.rowCount()):
                    vals = [self.dns_table.item(r, c).text() if self.dns_table.item(r, c) else "" for c in range(3)]
                    vals = ['"{}"'.format(v.replace('"', '""')) for v in vals]
                    f.write(",".join(vals) + "\n")

                f.write("\n== Discovered Subdomains ==\n")
                f.write("Subdomain,URL\n")
                for r in range(self.sub_table.rowCount()):
                    vals = [self.sub_table.item(r, c).text() if self.sub_table.item(r, c) else "" for c in range(2)]
                    vals = ['"{}"'.format(v.replace('"', '""')) for v in vals]
                    f.write(",".join(vals) + "\n")
            QMessageBox.information(self, "Export", f"Saved: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = DNSApp()
    w.resize(950, 700)
    w.show()
    sys.exit(app.exec_())
