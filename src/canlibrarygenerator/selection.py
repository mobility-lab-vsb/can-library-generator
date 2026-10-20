"""Database-aware selections usable by the GUI, tests and documentation tools."""


class DatabaseSelection:
    def __init__(self, databases, rx=True, tx=True):
        self.rows = {}
        self.parents = {}
        self.keys = {}
        self.selected_items = []
        self.message_modes = {}
        for db_index, db in enumerate(databases):
            for message_index, message in enumerate(db.messages):
                mid = f"db{db_index}:msg{message_index}"
                self.rows[mid] = ("Message", message.name)
                self.keys[mid] = (db_index, message.frame_id, message.is_extended_frame)
                self.message_modes[mid] = {"rx": rx, "tx": tx}
                for index, signal in enumerate(message.signals):
                    sid = f"{mid}:sig{index}"
                    self.rows[sid] = ("Signal", signal.name)
                    self.parents[sid] = mid
                    self.selected_items.append(sid)

    def item(self, item_id, option):
        kind, name = self.rows[item_id]
        return [kind] if option == "values" else name

    def parent(self, item_id):
        return self.parents[item_id]

    def message_key(self, item_id):
        return self.keys[item_id]
