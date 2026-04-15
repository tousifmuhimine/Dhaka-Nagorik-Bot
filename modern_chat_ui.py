#!/usr/bin/env python3
"""Improved Modern ChatGPT-style Flet UI with Resizable Sidebar."""
from __future__ import annotations

import flet as ft
from datetime import datetime


class ModernChatUI:
    """Modern chat interface with resizable sidebar and user dropdown."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.page.title = "Dhaka Nagorik AI - Chat"
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.padding = 0
        
        # Sidebar state
        self.sidebar_width = 280
        self.is_dragging = False
        self.drag_start_x = 0
        
        # Sample data
        self.current_user = "Suvigya"
        self.messages = []
        self.chat_column: ft.ListView | None = None
        self.message_input: ft.TextField | None = None
        self.sidebar_container: ft.Container | None = None
        self.divider: ft.GestureDetector | None = None

    def build(self) -> None:
        """Build the main UI."""
        self.page.clean()
        
        # Create sidebar
        sidebar = self._create_sidebar()
        self.sidebar_container = sidebar
        
        # Create resizable divider
        divider = self._create_divider()
        self.divider = divider
        
        # Create main chat area
        chat_area = self._create_chat_area()
        
        # Main layout with resizable sidebar
        main_layout = ft.Row(
            [sidebar, divider, chat_area],
            spacing=0,
            expand=True,
        )
        
        self.page.add(main_layout)
        
        # Add welcome message after page is ready
        self._add_bot_message(
            "Hello! I am Dhaka Nagorik AI. I can help you report civic complaints in Dhaka. What issue would you like to report?"
        )

    def _create_divider(self) -> ft.GestureDetector:
        """Create the resizable divider between sidebar and chat."""
        divider_container = ft.Container(
            width=6,
            bgcolor="#E0E0E0",
        )
        
        divider = ft.GestureDetector(
            content=divider_container,
            on_horizontal_drag_start=self._on_drag_start,
            on_horizontal_drag_update=self._on_drag_update,
            on_horizontal_drag_end=self._on_drag_end,
        )
        return divider

    def _on_drag_start(self, e: ft.DragStartEvent) -> None:
        """Handle drag start on divider."""
        self.is_dragging = True
        self.drag_start_x = e.local_x

    def _on_drag_update(self, e: ft.DragUpdateEvent) -> None:
        """Handle drag update on divider."""
        if not self.is_dragging:
            return

        # Calculate new width
        delta = e.delta_x
        new_width = self.sidebar_width + delta
        
        # Constrain width between 200px and 450px
        if 200 <= new_width <= 450:
            self.sidebar_width = new_width
            if self.sidebar_container:
                self.sidebar_container.width = self.sidebar_width
            self.page.update()

    def _on_drag_end(self, e: ft.DragEndEvent) -> None:
        """Handle drag end on divider."""
        self.is_dragging = False

    def _create_sidebar(self) -> ft.Container:
        """Create the left sidebar with user dropdown."""
        # User dropdown menu
        user_menu_items = [
            ft.PopupMenuItem(
                text="Profile",
                icon=ft.Icons.PERSON,
            ),
            ft.PopupMenuItem(
                text="Settings",
                icon=ft.Icons.SETTINGS,
            ),
            ft.PopupMenuItem(),  # Divider
            ft.PopupMenuItem(
                text="Logout",
                icon=ft.Icons.LOGOUT,
                on_click=self._logout_user,
            ),
        ]

        user_card = ft.Container(
            content=ft.Row(
                [
                    # Avatar
                    ft.Container(
                        content=ft.Text(
                            "S",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.WHITE,
                        ),
                        width=40,
                        height=40,
                        bgcolor="#1976D2",
                        border_radius=8,
                        alignment=ft.alignment.center,
                    ),
                    # User info
                    ft.Column(
                        [
                            ft.Text(
                                "Suvigya",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color="#1a1a1a",
                            ),
                            ft.Text("Citizen", size=11, color="#666"),
                        ],
                        spacing=2,
                    ),
                    # Dropdown menu button
                    ft.PopupMenuButton(
                        items=user_menu_items,
                        icon=ft.Icons.EXPAND_MORE,
                    ),
                ],
                spacing=12,
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=12,
            border=ft.border.all(1, "#E0E0E0"),
            border_radius=12,
            bgcolor="#FAFAFA",
        )

        sidebar_content = ft.Column(
            [
                user_card,
                ft.Container(height=20),
                ft.Text("Recent Chats", size=12, weight=ft.FontWeight.BOLD, color="#999"),
                ft.Container(height=8),
                ft.TextButton("New Complaint", icon=ft.Icons.ADD),
                ft.TextButton("View History", icon=ft.Icons.HISTORY),
                ft.TextButton("Settings", icon=ft.Icons.SETTINGS),
            ],
            spacing=0,
            expand=True,
        )

        sidebar = ft.Container(
            content=sidebar_content,
            padding=16,
            width=self.sidebar_width,
            bgcolor="#FAFAFA",
            border=ft.border.only(right=ft.BorderSide(1, "#E0E0E0")),
        )

        return sidebar

    def _create_chat_area(self) -> ft.Container:
        """Create the main chat area."""
        # Header
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(
                                "New Complaint",
                                size=18,
                                weight=ft.FontWeight.BOLD,
                                color="#1a1a1a",
                            ),
                            ft.Text(
                                "Started today at 2:30 PM",
                                size=11,
                                color="#999",
                            ),
                        ],
                        spacing=4,
                    ),
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.INFO_OUTLINE,
                                icon_size=20,
                            ),
                            ft.IconButton(
                                ft.Icons.MORE_VERT,
                                icon_size=20,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=16,
            border=ft.border.only(bottom=ft.BorderSide(1, "#E0E0E0")),
        )

        # Messages area with ListView for better scrolling
        self.chat_column = ft.ListView(
            spacing=12,
            auto_scroll=True,
            expand=True,
        )

        messages_container = ft.Container(
            content=self.chat_column,
            padding=16,
            bgcolor="#FFFFFF",
            expand=True,
        )

        # Input area
        input_area = self._create_input_area()

        # Chat area layout
        chat_area = ft.Container(
            content=ft.Column(
                [header, messages_container, input_area],
                spacing=0,
                expand=True,
            ),
            expand=True,
            bgcolor="#FFFFFF",
        )

        return chat_area

    def _create_input_area(self) -> ft.Container:
        """Create the message input area at the bottom."""
        self.message_input = ft.TextField(
            label="Type a new message here...",
            multiline=True,
            min_lines=1,
            max_lines=4,
            border_radius=12,
            filled=True,
            fill_color="#F5F5F5",
            border=ft.InputBorder.OUTLINE,
            expand=True,
        )

        input_row = ft.Row(
            [
                self.message_input,
                ft.IconButton(
                    ft.Icons.ATTACH_FILE,
                    icon_size=20,
                    tooltip="Attach file",
                ),
                ft.IconButton(
                    ft.Icons.EMOJI_EMOTIONS,
                    icon_size=20,
                    tooltip="Emoji",
                ),
                ft.IconButton(
                    ft.Icons.SEND,
                    icon_size=20,
                    tooltip="Send message",
                    on_click=self._on_send_message,
                ),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.END,
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

        input_container = ft.Container(
            content=input_row,
            padding=16,
            border=ft.border.only(top=ft.BorderSide(1, "#E0E0E0")),
            bgcolor="#FFFFFF",
            expand=True,
        )

        return input_container

    def _on_send_message(self, e) -> None:
        """Handle sending a message."""
        if not self.message_input or not self.message_input.value:
            return
        message = self.message_input.value.strip()
        if not message:
            return

        # Add user message
        self._add_user_message(message)

        # Clear input
        try:
            if self.message_input:
                self.message_input.value = ""
                self.message_input.focus()
        except Exception as e:
            print(f"Error clearing input: {e}")
        self.page.update()

        # Simulate bot response
        self._add_bot_message(
            "Thank you for reporting. Could you provide more details about the location and nature of the issue?"
        )
        self.page.update()

    def _add_user_message(self, text: str) -> None:
        """Add a user message to the chat."""
        if not self.chat_column:
            return
        message_bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        text,
                        size=14,
                        color=ft.Colors.WHITE,
                        selectable=True,
                        max_lines=None,
                    ),
                    ft.Text(
                        datetime.now().strftime("%I:%M %p"),
                        size=10,
                        color="rgba(255,255,255,0.7)",
                    ),
                ],
                spacing=4,
            ),
            padding=12,
            bgcolor="#1976D2",
            border_radius=16,
            width=500,
        )

        message_row = ft.Row(
            [
                ft.Container(expand=True),
                ft.Row(
                    [
                        message_bubble,
                        ft.Container(
                            content=ft.Text(
                                "S",
                                size=12,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.WHITE,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            width=32,
                            height=32,
                            bgcolor="#1976D2",
                            border_radius=8,
                        ),
                    ],
                    spacing=8,
                ),
            ],
            spacing=0,
        )

        self.chat_column.controls.append(message_row)

    def _add_bot_message(self, text: str) -> None:
        """Add a bot message to the chat."""
        if not self.chat_column:
            return
        message_bubble = ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        text,
                        size=14,
                        color="#1a1a1a",
                        selectable=True,
                        max_lines=None,
                    ),
                    ft.Text(
                        datetime.now().strftime("%I:%M %p"),
                        size=10,
                        color="#999",
                    ),
                ],
                spacing=4,
            ),
            padding=12,
            bgcolor="#E8E8E8",
            border_radius=16,
            width=500,
        )

        message_row = ft.Row(
            [
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(
                                "🤖",
                                size=18,
                            ),
                            width=32,
                            height=32,
                            alignment=ft.alignment.center,
                        ),
                        message_bubble,
                    ],
                    spacing=8,
                ),
                ft.Container(expand=True),
            ],
            spacing=0,
        )

        self.chat_column.controls.append(message_row)

    def _logout_user(self, e) -> None:
        """Handle user logout."""
        print("Logout clicked - placeholder function")
        # TODO: Implement actual logout logic
        # - Clear session
        # - Reset to login screen
        # - Navigate to home page
        self.page.snack_bar = ft.SnackBar(
            ft.Text("Logged out successfully", color=ft.Colors.WHITE)
        )
        self.page.snack_bar.open = True
        self.page.update()


def main(page: ft.Page) -> None:
    """Main entry point."""
    ui = ModernChatUI(page)
    ui.build()


if __name__ == "__main__":
    ft.app(target=main)
