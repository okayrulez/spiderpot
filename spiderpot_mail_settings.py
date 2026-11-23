"""Recipient enrollment dialog used by setup and settings."""

from queue import Empty, SimpleQueue
from threading import Thread
import tkinter as tk
from tkinter import ttk

from spiderpot_mail import MailClient, MailError


class MailSettings(ttk.LabelFrame):
    def __init__(self, parent, url, enrollment, on_confirm):
        super().__init__(parent, text="E-posta bildirimleri", padding=12, style="Setup.TLabelframe")
        self.client = MailClient(url) if url else None
        self.enrollment = enrollment
        self.on_confirm = on_confirm
        self.results = SimpleQueue()
        self.poll_job = None
        self.challenge = ''
        self.columnconfigure(1, weight=1)
        self.address = tk.StringVar(self, value=enrollment['email'] if enrollment else '')
        ttk.Label(self, text='Alıcı e-posta adresi', style='Setup.TLabel').grid(row=0, column=0, sticky='w', padx=(0,8))
        self.email = ttk.Entry(self, width=18, textvariable=self.address)
        self.email.grid(row=0, column=1, sticky='ew')
        self.request_button = ttk.Button(self, text='Kod gönder', command=self.request_code)
        self.request_button.grid(row=0, column=2, sticky='ew', padx=(8,0))
        ttk.Label(self, text='6 haneli kod', style='Setup.TLabel').grid(row=1, column=0, sticky='w')
        self.code = ttk.Entry(self, width=12, state='disabled')
        self.code.grid(row=1, column=1, sticky='w', pady=6)
        self.verify_button = ttk.Button(self, text='Doğrula', command=self.confirm, state='disabled')
        self.verify_button.grid(row=1, column=2, sticky='ew', padx=(8,0))
        self.status = ttk.Label(self, style='Muted.Setup.TLabel', wraplength=350)
        self.status.grid(row=2, column=0, columnspan=2, sticky='w')
        self.remove = ttk.Button(self, text='Kapat', command=lambda: self.select(None))
        self.remove.grid(row=2, column=2, sticky='e')
        self.address.trace_add('write', self.address_changed)
        self.select(enrollment)

    def select(self, enrollment):
        self.enrollment = enrollment
        self.challenge = ''
        self.on_confirm(enrollment)
        self.address.set(enrollment['email'] if enrollment else '')
        self.code.configure(state='normal')
        self.code.delete(0, 'end')
        self.code.configure(state='disabled')
        self.verify_button.configure(state='disabled')
        self.request_button.configure(state='normal' if self.client else 'disabled')
        self.remove.configure(state='normal' if enrollment else 'disabled')
        self.status.configure(text='Adres doğrulandı.' if enrollment else
                              'İsteğe bağlı. Etkinlikte yalnızca metin gönderilir.' if self.client else 'E-posta servisi yapılandırılmadı.')

    def ready_to_save(self):
        if self.poll_job is not None:
            return False
        return self.address.get().strip() == (self.enrollment['email'] if self.enrollment else '')

    def address_changed(self, *_):
        if self.challenge and self.email.get().strip() != self.pending_email:
            self.challenge = ''
            self.code.configure(state='disabled')
            self.verify_button.configure(state='disabled')
            self.status.configure(text='Bu adres için yeni bir kod isteyin.')

    def request_code(self):
        self.pending_email = self.email.get().strip()
        if not self.pending_email:
            self.status.configure(text='Alıcı e-posta adresini girin.')
            return
        self.challenge = ''
        self.run('request', self.client.request_code, self.pending_email)

    def confirm(self):
        code = self.code.get().strip()
        if len(code) != 6 or not code.isascii() or not code.isdigit():
            self.status.configure(text='E-postadaki altı haneli kodu girin.')
            return
        self.run('confirm', self.client.confirm, self.challenge, code)

    def run(self, action, operation, *arguments):
        for widget in (self.email, self.code, self.request_button, self.verify_button):
            widget.configure(state='disabled')
        self.remove.configure(state='disabled')
        self.status.configure(text='İşleniyor…')

        def worker():
            try:
                result = operation(*arguments)
                self.results.put((action, result, ''))
            except MailError as error:
                self.results.put((action, '', str(error)))

        Thread(target=worker, daemon=True).start()
        self.poll_job = self.after(70, self.poll)

    def poll(self):
        try:
            action, result, error = self.results.get_nowait()
        except Empty:
            self.poll_job = self.after(70, self.poll)
            return
        self.poll_job = None
        if error:
            self.status.configure(text=error)
        elif action == 'request':
            self.challenge = result
            self.status.configure(text='Kod gönderildi. Gelen kutunuzu kontrol edin.')
            self.code.configure(state='normal')
            self.code.delete(0, 'end')
            self.code.focus_set()
        else:
            self.select({'url': self.client.url, 'email': self.pending_email, 'token': result})
            self.email.configure(state='normal')
            return
        self.email.configure(state='normal')
        self.request_button.configure(state='normal')
        self.remove.configure(state='normal' if self.enrollment else 'disabled')
        if self.challenge:
            self.code.configure(state='normal')
            self.verify_button.configure(state='normal')

