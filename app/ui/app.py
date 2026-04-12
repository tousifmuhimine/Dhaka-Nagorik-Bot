"""UI for Dhaka Civic Complaint System."""
from __future__ import annotations
import flet as ft
import httpx

API_BASE_URL = "http://127.0.0.1:8000/api"

class DhakaBot:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.http_client = httpx.Client()
        self.page.title = "Dhaka Civic Complaint System"
        self.page.bgcolor = "#FFFFFF"
        self.current_user = None
    
    def build(self):
        self.show_home_page()
    
    def show_home_page(self) -> None:
        self.page.clean()
        name_input = ft.TextField(label="Enter name", width=300)
        def proceed(_):
            name = name_input.value.strip()
            if name:
                self.show_role_selection(name)
            else:
                self.show_snackbar("Enter name")
        self.page.add(ft.Container(content=ft.Column([
            ft.Text("Dhaka Civic Complaint System", size=40, weight=ft.FontWeight.BOLD, color="#1a1a1a", text_align=ft.TextAlign.CENTER),
            ft.Text("Report complaints efficiently", size=14, color="#666", text_align=ft.TextAlign.CENTER),
            ft.Container(height=40),
            name_input,
            ft.ElevatedButton("Continue", width=300, height=50, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8), bgcolor="#1976D2", color=ft.Colors.WHITE), on_click=proceed),
        ], spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER), padding=60, alignment=ft.alignment.center, expand=True))
    
    def show_role_selection(self, name: str) -> None:
        self.page.clean()
        def go(role):
            if role == "authority":
                self.show_authority_login(name)
            else:
                self.show_login(name, role)
        self.page.add(ft.Container(content=ft.Column([
            ft.Text(f"Welcome, {name}!", size=32, weight=ft.FontWeight.BOLD),
            ft.Text("Select role", size=14, color="#666"),
            ft.Container(height=30),
            ft.ElevatedButton("Citizen", width=250, height=45, on_click=lambda _: go("citizen")),
            ft.ElevatedButton("Authority", width=250, height=45, on_click=lambda _: go("authority")),
            ft.ElevatedButton("Admin", width=250, height=45, on_click=lambda _: go("admin")),
            ft.TextButton("Back", on_click=lambda _: self.show_home_page()),
        ], spacing=16, horizontal_alignment=ft.CrossAxisAlignment.CENTER, alignment=ft.MainAxisAlignment.CENTER), padding=60, expand=True))
    
    def show_login(self, name: str, role: str) -> None:
        self.page.clean()
        email = ft.TextField(label="Email", width=300)
        pwd = ft.TextField(label="Password", password=True, width=300)
        def submit(_):
            if email.value and pwd.value:
                user_id = f"{role}_{email.value}".replace("@", "_").replace(".", "_")
                self.current_user = {"name": name, "email": email.value, "role": role, "user_id": user_id}
                if role == "citizen":
                    self.show_citizen_page()
                else:
                    self.show_admin_page()
            else:
                self.show_snackbar("Fill all")
        self.page.add(ft.Container(content=ft.Column([
            ft.Text(f"{role.title()}", size=28, weight=ft.FontWeight.BOLD),
            email, pwd,
            ft.ElevatedButton("Sign In", width=300, height=50, style=ft.ButtonStyle(bgcolor="#1976D2", color=ft.Colors.WHITE), on_click=submit),
            ft.TextButton("Back", on_click=lambda _: self.show_role_selection(name)),
        ], spacing=16), padding=40))
    
    def show_authority_login(self, name: str) -> None:
        self.page.clean()
        email = ft.TextField(label="Email", width=300)
        pwd = ft.TextField(label="Password", password=True, width=300)
        thana_opt = ft.Dropdown(label="Thana", width=300, options=[ft.dropdown.Option(t) for t in ["Mirpur", "Kotwali", "Dhanmondi"]])
        def submit(_):
            if email.value and pwd.value and thana_opt.value:
                user_id = f"authority_{email.value}".replace("@", "_").replace(".", "_")
                self.current_user = {"name": name, "email": email.value, "role": "authority", "thana": thana_opt.value, "user_id": user_id}
                self.show_authority_page()
            else:
                self.show_snackbar("Fill all")
        self.page.add(ft.Container(content=ft.Column([
            ft.Text("Authority", size=28, weight=ft.FontWeight.BOLD),
            email, pwd, thana_opt,
            ft.ElevatedButton("Login", width=300, height=50, style=ft.ButtonStyle(bgcolor="#1976D2", color=ft.Colors.WHITE), on_click=submit),
            ft.TextButton("Back", on_click=lambda _: self.show_role_selection(name)),
        ], spacing=16), padding=40))
    
    def show_citizen_page(self) -> None:
        self.page.clean()
        chat = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
        inp = ft.TextField(label="Type...", multiline=True, min_lines=2, max_lines=4)
        conversation_id = None
        
        def send(_):
            nonlocal conversation_id
            msg = inp.value.strip()
            if not msg:
                return
            
            chat.controls.append(ft.Container(content=ft.Text(msg, color=ft.Colors.WHITE, size=11), bgcolor="#1976D2", padding=10))
            inp.value = ""
            self.page.update()
            
            try:
                headers = {
                    "X-User-Id": self.current_user["user_id"],
                    "X-User-Role": self.current_user["role"]
                }
                
                if not conversation_id:
                    resp = self.http_client.post(f"{API_BASE_URL}/chat/start", json={"initial_message": msg}, headers=headers)
                    if resp.status_code == 200:
                        conversation_id = resp.json().get("conversation_id")
                    else:
                        chat.controls.append(ft.Container(content=ft.Text(f"Error: {resp.status_code}", color="#1a1a1a", size=10), bgcolor="#FFE0E0", padding=10))
                        self.page.update()
                        return
                
                if conversation_id:
                    resp = self.http_client.post(f"{API_BASE_URL}/chat/{conversation_id}/message", json={"message": msg}, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        assistant_msg = data.get("assistant_message", "Thanks for your input.")
                        chat.controls.append(ft.Container(content=ft.Text(assistant_msg, color="#1a1a1a", size=11), bgcolor="#E0E0E0", padding=10))
                    else:
                        error_detail = resp.json().get("detail", "Unknown error")
                        chat.controls.append(ft.Container(content=ft.Text(f"API Error: {error_detail}", color="#1a1a1a", size=10), bgcolor="#FFE0E0", padding=10))
            except Exception as e:
                chat.controls.append(ft.Container(content=ft.Text(f"Error: {str(e)[:50]}", color="#1a1a1a", size=10), bgcolor="#FFE0E0", padding=10))
            
            self.page.update()
        
        self.page.add(ft.Container(content=ft.Column([
            ft.Text(f"Hi {self.current_user['name']}", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(content=chat, bgcolor="#FAFAFA", padding=12, expand=True),
            ft.Row([ft.Container(inp, expand=True), ft.IconButton(ft.Icons.SEND, on_click=send)], spacing=8),
            ft.Row([ft.TextButton("History"), ft.TextButton("Logout", on_click=lambda _: self.show_home_page())]),
        ], spacing=12, expand=True), padding=16))
    
    def show_authority_page(self) -> None:
        self.page.clean()
        self.page.add(ft.Container(content=ft.Column([ft.Text(f"Thana: {self.current_user['thana']}", size=18, weight=ft.FontWeight.BOLD), ft.Text("Complaints list"), ft.TextButton("Logout", on_click=lambda _: self.show_home_page())], expand=True), padding=16))
    
    def show_admin_page(self) -> None:
        self.page.clean()
        self.page.add(ft.Container(content=ft.Column([ft.Text("Admin Dashboard", size=18, weight=ft.FontWeight.BOLD), ft.Text("All complaints"), ft.TextButton("Logout", on_click=lambda _: self.show_home_page())], expand=True), padding=16))
    
    def show_snackbar(self, msg: str) -> None:
        self.page.snack_bar = ft.SnackBar(ft.Text(msg))
        self.page.snack_bar.open = True
        self.page.update()

def main(page: ft.Page) -> None:
    app = DhakaBot(page)
    app.build()

if __name__ == "__main__":
    ft.app(target=main)
