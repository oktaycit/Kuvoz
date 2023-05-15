import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
import json


class CenteredTextInput(TextInput):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.text_align = 'bottom'
        self.font_size =24


class SaveDataApp(App):
    def build(self):
        # set window properties
        Window.size = (800, 420)
        Window.clearcolor = (0.2, 0.5, 0.7, 1)

        # create main layout
        layout = GridLayout(cols=2, size_hint=(1, None), height=400, spacing=(10, 10))

        # create labels and inputs for data
        broker_label = Label(text="Broker", font_size=20)
        broker_input = CenteredTextInput(text='', multiline=False)
        port_label = Label(text="Port", font_size=20)
        port_input = CenteredTextInput(text='', multiline=False)
        topic_label = Label(text="Topic", font_size=20)
        topic_input = CenteredTextInput(text='', multiline=False)
        client_id_label = Label(text="Client ID", font_size=20)
        client_id_input = CenteredTextInput(text='', multiline=False)
        username_label = Label(text="Username", font_size=20)
        username_input = CenteredTextInput(text='', multiline=False)
        password_label = Label(text="Password", font_size=20)
        password_input = CenteredTextInput(text='', multiline=False, password=True)

        # add inputs to layout
        layout.add_widget(broker_label)
        layout.add_widget(broker_input)
        layout.add_widget(port_label)
        layout.add_widget(port_input)
        layout.add_widget(topic_label)
        layout.add_widget(topic_input)
        layout.add_widget(client_id_label)
        layout.add_widget(client_id_input)
        layout.add_widget(username_label)
        layout.add_widget(username_input)
        layout.add_widget(password_label)
        layout.add_widget(password_input)

        # check if connect.json file exists and load data
        try:
            with open('connect.json', 'r') as f:
                data = json.load(f)
                broker_input.text = data["broker"]
                port_input.text = str(data["port"])
                topic_input.text = data["topic"]
                client_id_input.text = data["client_id"]
                username_input.text = data["username"]
                password_input.text = data["password"]
        except FileNotFoundError:
            pass

        # create save button
        def save_data(instance):
            data = {
                "broker": broker_input.text,
                "port": port_input.text,
                "topic": topic_input.text,
                "client_id": client_id_input.text,
                "username": username_input.text,
                "password": password_input.text
            }
            with open('connect.json', 'w') as f:
                json.dump(data, f)
            # ~ broker_input.text = ''
            # ~ port_input.text = ''
            # ~ topic_input.text = ''
            # ~ client_id_input.text = ''
            # ~ username_input.text = ''
            # ~ password_input.text = ''
            self.stop()
        save_button = Button(text='Save & Exit')
        save_button.bind(on_press=save_data)
        layout.add_widget(save_button)

        return layout

if __name__ == '__main__':
    SaveDataApp().run()
