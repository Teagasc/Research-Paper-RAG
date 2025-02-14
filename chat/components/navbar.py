import reflex as rx
from chat.state import State

def navbar():
    return rx.box(
        rx.hstack(
            # LEFT SECTION: Avatar, title, and current chat badge.
            rx.hstack(
                rx.avatar(fallback="RPA", variant="solid"),
                rx.heading("Research Paper Assistant"),
                rx.desktop_only(
                    rx.badge(
                        State.current_chat,
                        rx.tooltip(
                            rx.icon("info", size=14),
                            content="The current selected chat."
                        ),
                        variant="soft"
                    )
                ),
                align_items="center",
            ),
            # RIGHT SECTION: New Chat Modal and Documents Modal.
            rx.hstack(
                # New Chat Modal using rx.dialog.
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("+ New chat")
                    ),
                    rx.dialog.content(
                        rx.hstack(
                            rx.input(
                                placeholder="Chat title...",
                                on_blur=State.set_new_chat_name,
                                width=["15em", "20em", "30em", "30em", "30em", "30em"],
                            ),
                            rx.dialog.close(
                                rx.button("Create chat", on_click=State.create_chat)
                            ),
                            background_color=rx.color("mauve", 1),
                            spacing="2",
                            width="100%"
                        )
                    )
                ),
                # Documents Modal using rx.dialog.
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("Documents")
                    ),
                    rx.dialog.content(
                        rx.cond(
                            # When no document is selected, show "All Documents" button + list of documents.
                            State.selected_document == None,
                            rx.box(
                                rx.button(
                                    "All Documents",
                                    on_click=State.clear_selected_document,
                                    width="100%",
                                    margin_bottom="0.5em",
                                    variant="outline"
                                ),
                                rx.foreach(
                                    State.documents,
                                    lambda doc: rx.button(
                                        doc["name"],
                                        on_click=lambda doc=doc: State.select_document(doc),
                                        width="100%",
                                        margin_bottom="0.5em",
                                        variant="outline"
                                    )
                                )
                            ),
                            # When a document is selected, show its name and an "All Documents" button.
                            rx.box(
                                rx.button(
                                    "All Documents",
                                    on_click=State.clear_selected_document,
                                    margin_bottom="1em"
                                ),
                                rx.text(State.selected_document_text)
                            )
                        ),
                        max_height="70vh",      # Limit modal content height to 70% of viewport.
                        overflow_y="auto",       # Enable scrolling if needed.
                        padding="1em",
                        background_color=rx.color("mauve", 2)
                    )
                ),
            ),
            justify_content="space-between",
            align_items="center",
        ),
        backdrop_filter="auto",
        backdrop_blur="lg",
        padding="12px",
        border_bottom=f"1px solid {rx.color('mauve', 3)}",
        background_color=rx.color("mauve", 2),
        position="sticky",
        top="0",
        z_index="100",
        align_items="center",
    )
