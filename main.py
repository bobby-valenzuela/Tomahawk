from textual.app import App, ComposeResult
from textual.containers import Horizontal,Vertical, VerticalScroll
from textual.widgets import Label,Button,RichLog,TabbedContent,TabPane,Select,Footer,Header
from textual.binding import Binding
from textual import on
from functions import (
        get_hosts,
        get_service_state,
        send_ssh_cmd,
        get_ssh_hosts,
        enable_host,
        remove_host,
        is_host_enabled
)


class ServiceButtons(Vertical):


    def get_apache_status(self):
        return get_service_state("apache",self.host_name)

    def update_service_details(self,svc_state):
        label = self.query_one(".host-header-label",Button)
        label.label = f"{svc_state}"
        start_btn = self.query_one("#start-service")
        stop_btn = self.query_one("#stop-service")
        load_btn = self.query_one("#loading-service")
        load_btn.add_class("d-none")

        # Apply colored border
        label.remove_class("border-top-info")
        label.remove_class("border-top-success")
        label.remove_class("border-top-error")
        if svc_state == "Active":
            label.add_class("border-top-success")
            start_btn.add_class("d-none")
            stop_btn.remove_class("d-none")
        elif svc_state == "Inactive":
            label.add_class("border-top-error")
            start_btn.remove_class("d-none")
            stop_btn.add_class("d-none")
        else:
            label.add_class("border-top-info")

        # ENABLED DISABLED BTNS
        restart_btn = self.query_one("#restart-service")
        remove_btn = self.query_one("#remove-host")
        fetch_btn = self.query_one("#fetch-logs")
        restart_btn.disabled = False
        remove_btn.disabled = False
        fetch_btn.disabled = False
        
    # def on_show(self) -> None:
    #     self.update_service_details()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        event.button.disabled=True
        if button_id == "start-service":
            response = send_ssh_cmd(self.host_name,"sudo systemctl start apache2 && echo 1")
            if response == '1':
                self.update_service_details("Active")
            self.notify("Apache service started!", severity="success", timeout=5, title="Apache Service")

        elif button_id == "stop-service":
            response = send_ssh_cmd(self.host_name,"sudo systemctl stop apache2 && echo 1")
            if response == '1':
                self.update_service_details("Inactive")
            self.notify("Apache service stopped!", severity="error", timeout=5, title="Apache Service")
        elif button_id == "restart-service":
            response = send_ssh_cmd(self.host_name,"sudo systemctl restart apache2 && echo 1")
            if response == '1':
                self.update_service_details("Active")
            self.notify("Apache service restarted!", severity="success", timeout=5, title="Apache Service")
        elif button_id == "status-btn":
            state = self.get_apache_status()
            self.update_service_details(state)
            self.notify("Apache state refreshed!", severity="information", timeout=5, title="Apache Service")
        elif button_id == "remove-host":
            remove_host(self.host_name)

        # re-enable pressed btn
        if button_id != "remove-host":
            event.button.disabled=False

    def compose(self) -> ComposeResult:
        self.host_name = f"{self.id}".replace("svc-btns-","")
        # connections = send_ssh_cmd(self.host_name,"netstat -ant | grep -E -e :80 -e :443 | grep ESTABLISHED | wc -l")
        # service_enabled_state = send_ssh_cmd(self.host_name,"systemctl is-enabled apache2")
        # connections = 100
        # service_enabled_state = 'Active'

        yield Horizontal(
                Button(label="Start/Stop",id="loading-service",variant="default", disabled=True),
                Button(label="Start",id="start-service",variant="success", classes="d-none",tooltip="Start the apache service"),
                Button(label="Stop",id="stop-service", variant="error", classes="d-none", tooltip="Stop the apache service"),
                Button(label="Restart",id="restart-service", variant="primary", classes=" margin-left-1", disabled=True,tooltip="Restart the apache service"),
                Horizontal( Button("Check status",classes="text-aligh-center host-header-label border-top-info margin-left-1",id="status-btn",tooltip="Click to check/refresh status"),),
                Button(label="Fetch logs",classes="w-100 get-logs margin-left-1",disabled=True,id="fetch-logs",variant="default",tooltip="Fetch latest 25 logs"),
                Button(label="Remove",id="remove-host",classes="margin-left-1", variant="error",tooltip="Remove this host from the list"),
        )

       

class HeaderService(Horizontal):

    def compose(self) -> ComposeResult:
        self.host_name = f"{self.id}".replace("header-svc-","")

        yield Horizontal(
            Label(f"Host {self.host_name}",classes="heading-primary"), 
            # Button("x",classes="dock-right sm-btn",variant="error")
        )


class ServiceController(Vertical):


    def compose(self) -> ComposeResult:
        self.host_name = f"{self.id}".replace("svc-controller-","")
        yield HeaderService(id=f"header-svc-{self.host_name}",classes="header-title")
        yield ServiceButtons(id=f"svc-btns-{self.host_name}",classes="service-btns")


class Host(Horizontal):
    """Host Widget"""

    def parse_logs(self,log_data):
        # Split the content based on delimiters
        parts = log_data.split('fin-error')
        error_part = parts[0].strip()  # Everything before fin-error

        # Split the remaining part at fin-access
        remaining = parts[1].split('fin-access')
        access_part = remaining[0].strip()  # Between fin-error and fin-access
        service_part = remaining[1].strip()  # After fin-access

        return error_part, access_part, service_part

    def refresh_all_logs(self,option) -> None:
        log_count = 25
        svc_log = self.query_one("#service-log")
        acc_log = self.query_one("#access-log")
        err_log = self.query_one("#error-log")
        svc_log.clear()
        acc_log.clear()
        err_log.clear()

        # Get logs in one command
        log_content = send_ssh_cmd(self.host_name,f"tail -n {log_count} /var/log/apache2/error.log && echo fin-error && tail -n {log_count} /var/log/apache2/access.log && echo fin-access && journalctl -u apache2 -n {log_count}")

        latest_err_logs,latest_acc_logs,latest_svc_logs = self.parse_logs(log_content)

        svc_log.write(latest_svc_logs,animate=True,scroll_end=True)
        acc_log.write(latest_acc_logs,animate=True,scroll_end=True)
        err_log.write(latest_err_logs,animate=True,scroll_end=True)

        if option != "no-toast":
            self.notify("Logs Fetched!", severity="success", timeout=5, title="Logging Update")


    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "fetch-logs":
            if self.has_class("expanded"):
                self.refresh_all_logs("toast")
            else:
                self.add_class("expanded")
                content_switcher = self.query_one("#tabbed-content-logs")
                content_switcher.remove_class("d-none")
                self.refresh_all_logs("no-toast")
                self.notify("logs Fetched!", severity="success", timeout=5, title="Logging Update")
        elif button_id == "remove-host":
            self.remove()
            self.refresh()
            self.notify("Host Removed!", severity="error", timeout=5, title="Hosts")


    def compose(self) -> ComposeResult:
        """Create host widgets(s)"""
        self.host_name = f"{self.id}".replace("host-","")
        yield ServiceController(id=f"svc-controller-{self.host_name}",classes="ServiceController w-100")
        with TabbedContent(classes="margin-top-1 d-none",id="tabbed-content-logs"):
            with TabPane("service"):
                yield RichLog(max_lines=25,auto_scroll=True,wrap=True,classes="LogReader w-100",id="service-log",highlight=True,markup=True)
            with TabPane("access.log"):
                yield RichLog(max_lines=25,auto_scroll=True,wrap=True,classes="LogReader w-100",id="access-log",highlight=True)
            with TabPane("error.log"):
                yield RichLog(max_lines=25,auto_scroll=True,wrap=True,classes="LogReader w-100",id="error-log",highlight=True)

    # def on_show(self) -> None:
    #     self.refresh_all_logs("no-toast")

    # def on_mount(self) -> None:
    #     acc_log = self.query_one("#access-log")
    #     err_log = self.query_one("#error-log")
    #     svc_log = self.query_one("#service-log")
    #     svc_log.write("Fetching...",animate=True,scroll_end=True)
    #     acc_log.write("Fetching...",animate=True,scroll_end=True)
    #     err_log.write("Fetching...",animate=True,scroll_end=True)


class Tomahawk(App):
    """App to manage host widgets"""

    CSS_PATH = "style.tcss"

    BINDINGS = [
        Binding(key="^q", action="quit", description="Quit the app"),
        # Binding(
        #     key="question_mark",
        #     action="help",
        #     description="Show help screen",
        #     key_display="?",
        # ),
        # Binding(key="delete", action="delete", description="Delete the thing"),
        # Binding(key="j", action="down", description="Scroll down", show=False),
    ]


    def get_host_data(self):
        self.hosts = get_hosts()


    def compose(self) -> ComposeResult:

        """Create host widgets(s)"""
        yield Header()
        self.get_host_data()
        saved_hosts = [ Host(classes="hostBox", id=f"host-{name[0]}") for name in self.hosts ]
        yield VerticalScroll( *saved_hosts , id="host-container")

        # add host select
        yield Label("Add Host",classes="margin-left-1")
        LINES=get_ssh_hosts()
        yield Select.from_values(LINES, id="host-select",classes="margin-bottom-5")

        # yield Label("Quit: ctrl+q",classes="margin-left-1 margin-bottom-1")
        yield Footer()

    @on(Select.Changed)
    def select_changed(self, event: Select.Changed) -> None:
        if event.value != Select.BLANK:

            if not is_host_enabled(event.value):
                enable_host(event.value)
                new_host = Host(classes="hostBox", id=f"host-{event.value}")

                # Add it to the container
                container = self.query_one("#host-container")
                container.mount(new_host)
                self.notify("Added Host!", severity="success", timeout=5, title="Hosts")
                # Reset the Select widget to its default value
                select_widget = self.query_one("#host-select", Select)
                select_widget.value = Select.BLANK
                self.refresh()







if __name__ == "__main__":
    app = Tomahawk()
    app.run()
