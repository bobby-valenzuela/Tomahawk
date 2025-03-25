import sqlite3
import subprocess
import os


def get_hosts():
    con = sqlite3.connect("tomahawk.db")
    res = con.execute("SELECT hostname FROM hosts WHERE isEnabled=1")
    data =  res.fetchall()
    con.close()
    return data

def remove_host(host_name):
    con = sqlite3.connect("tomahawk.db")
    cursor = con.cursor()
    cursor.execute(f"UPDATE hosts SET isEnabled=0 WHERE hostname='{host_name}'")
    con.commit()
    con.close()

def enable_host(host_name):
    con = sqlite3.connect("tomahawk.db")
    cursor = con.cursor()
    # See if an entry already saved to be service_enabled
    if is_host_saved(host_name):
        # re-enable
        cursor.execute(f"UPDATE hosts SET isEnabled=1 WHERE hostname='{host_name}'")
        con.commit()
    else:
        # insert
        cursor.execute(f"INSERT INTO hosts (hostname,isEnabled) VALUES('{host_name}',1)")
        con.commit()

    con.close()

def is_host_saved(host_name):
    con = sqlite3.connect("tomahawk.db")
    res = con.execute(f"SELECT COUNT(hostname) FROM hosts WHERE hostname='{host_name}'")
    matches = res.fetchone()
    con.close()
    return matches[0] > 0

def is_host_enabled(host_name):
    con = sqlite3.connect("tomahawk.db")
    res = con.execute(f"SELECT COUNT(hostname) FROM hosts WHERE hostname='{host_name}' AND isEnabled=1")
    matches = res.fetchone()
    con.close()
    return matches[0] > 0

def get_service_state(service,host_name):

    if test_ssh_connection(host_name):

        service_name = ''

        if service == "apache":
            # Apache service name varies by distribution: 'apache2' (Debian/Ubuntu) or 'httpd' (RHEL/CentOS/Fedora)
            service_name = "apache2"  # Change to "httpd" if using RHEL-based distro
        else:
            return "n/a"
        
        try:
            # Run systemctl is-active to check the service state
            result = subprocess.run(
                f"ssh {host_name} 'systemctl is-active {service_name} 2>/dev/null' ",
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                timeout=5  # Timeout after 10 seconds to avoid hanging
            )
            # The output will be "active" or "inactive" (or "failed" in some cases)
            state = result.stdout.strip().capitalize()
            
            
            if state == "Active" or state == "Inactive":
                return state
            else:
                return f"Error: {state}"
        
        except Exception as e:
            # print(f"Error: {str(e)}")
            return "An error ocurred"

    else:
        return "Failed to conect via SSH"

def test_ssh_connection(host_name):
    try:
        # Run a simple command over SSH
        result = subprocess.run(
            ["ssh", host_name, "echo test"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5  # Timeout after 10 seconds to avoid hanging
        )
        
        # Check the result
        if result.returncode == 0 and result.stdout.strip() == "test":
            return True
        else:
            return False
    
    except subprocess.TimeoutExpired:
        # print(f"SSH connection to {host_name} timed out")
        return False
    except Exception as e:
        # print(f"Error testing SSH: {str(e)}")
        return False


def send_ssh_cmd(host_name, cmd):
    
    try:
        result = subprocess.run(
            f"ssh {host_name} '{cmd} 2>/dev/null' ",
            shell=True,
            capture_output=True,
            text=True,
            check=False,
            timeout=10  # Timeout after 10 seconds to avoid hanging
        )
        return result.stdout.strip()
        
    except Exception as e:
        return f"Error: {str(e)}"

def get_ssh_hosts():

    # Path to the SSH config file
    config_path = os.path.expanduser("~/.ssh/config")
    
    # Initialize an empty list to store hosts
    hosts = []
    
    try:
        # Open and read the file
        with open(config_path, "r") as file:
            for line in file:
                # Strip whitespace and check if line starts with "Host"
                line = line.strip()
                if line.startswith("Host ") :
                    # Make sure host is already enabled - otherwise skip it yo
                    # Add all hostnames (supporting multiple on one line)
                    hostname = line.replace("Host","").strip()
                    if not is_host_enabled(hostname):
                        hosts.append(hostname)
        
        # Join hosts with newlines
        return "\n".join(hosts).splitlines()
    
    except FileNotFoundError:
        return "Error: ~/.ssh/config file not found"
    except PermissionError:
        return "Error: Permission denied to read ~/.ssh/config"
    except Exception as e:
        return f"Error: {str(e)}"

