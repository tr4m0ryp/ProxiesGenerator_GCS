# ProxiesGenerator_GCS
Proxies maker by creating VM's on google cloud console

### **Step 1: Prerequisites**
Before you run the script, ensure you have the following:
- **Google Cloud SDK Installed:** This includes the `gcloud` command-line tool and Python client libraries.
- **Google Cloud Project:** Ensure you have a project set up and that you have billing enabled.
- **API Access:** Enable the Compute Engine API for your project.
- **Service Account or User Authentication:** You need to be authenticated with Google Cloud using a service account or your user credentials.

### **Step 2: Install Required Python Libraries**
Make sure you have the necessary Python libraries installed:

```bash
pip install google-auth google-cloud-compute
```

These libraries allow your Python script to interact with Google Cloud's Compute Engine.

### **Step 3: Understand the Script**

#### **Imports**
The script starts by importing necessary libraries:

```python
import google.auth
from google.cloud import compute_v1
from google.auth.transport.requests import Request
```

- `google.auth` handles authentication.
- `compute_v1` is the module for interacting with Compute Engine.
- `Request` is used for making authorized requests.

#### **Function to Create a VM Instance**
```python
def create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script):
```
This function creates a single VM instance. Here's a breakdown:

1. **Instance Configuration:**
   ```python
   instance = compute_v1.Instance()
   instance.name = instance_name
   instance.zone = zone
   instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"
   ```

   - **Instance Name:** Each VM is named using a base name with a unique identifier (e.g., `proxy-1`, `proxy-2`).
   - **Machine Type:** Defines the type of VM (e.g., `f1-micro`).

2. **Set the Instance as Preemptible:**
   ```python
   scheduling = compute_v1.Scheduling()
   scheduling.preemptible = True
   instance.scheduling = scheduling
   ```

   - **Preemptible VM:** This setting makes the instance cheaper but subject to termination by Google Cloud.

3. **Disk Configuration:**
   ```python
   disk = compute_v1.AttachedDisk()
   initialize_params = compute_v1.AttachedDiskInitializeParams()
   initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
   disk.initialize_params = initialize_params
   disk.boot = True
   disk.auto_delete = True
   disk.type_ = compute_v1.AttachedDisk.Type.PERSISTENT
   instance.disks = [disk]
   ```

   - **Boot Disk:** Configures the disk from which the VM will boot.
   - **Auto-delete:** The disk is deleted when the instance is deleted.

4. **Network Configuration:**
   ```python
   network_interface = compute_v1.NetworkInterface()
   access_config = compute_v1.AccessConfig()
   access_config.name = "External NAT"
   access_config.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT
   access_config.network_tier = "PREMIUM"
   network_interface.access_configs = [access_config]
   network_interface.name = "global/networks/default"
   instance.network_interfaces = [network_interface]
   ```

   - **External IP Address:** An ephemeral external IP address is automatically assigned.
   - **Network Interface:** Connects the VM to the default network.

5. **Metadata and Startup Script:**
   ```python
   metadata = compute_v1.Metadata()
   items = [compute_v1.Items(
       key="startup-script",
       value=startup_script
   )]
   metadata.items = items
   instance.metadata = metadata
   ```

   - **Startup Script:** This script runs automatically when the VM starts. It can be used to install software, configure settings, etc.

6. **Create the Instance:**
   ```python
   operation = compute.insert(project=project, zone=zone, instance_resource=instance)
   print(f"Waiting for operation {operation.name} to finish...")
   wait_for_operation(compute, project, zone, operation.name)
   ```

   - **Instance Creation:** The VM is created in the specified zone.
   - **Wait for Completion:** The script waits until the instance is fully created.

#### **Function to Wait for Operation Completion**
```python
def wait_for_operation(compute, project, zone, operation):
    while True:
        result = compute.zone_operations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if 'error' in result:
            raise Exception(result['error'])
        if result['status'] == 'DONE':
            print("Operation complete.")
            return
```

- **Polling:** This function checks the status of the creation operation until it completes.

#### **Function to Create Multiple VMs**
```python
def create_multiple_vms(project, zone, instance_base_name, num_instances, machine_type, image_family, image_project, startup_script):
    credentials, project_id = google.auth.default()
    compute = compute_v1.InstancesClient(credentials=credentials)

    for i in range(1, num_instances + 1):
        instance_name = f"{instance_base_name}-{i}"
        create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script)
```

- **Credentials:** Authenticates with Google Cloud.
- **Loop:** Creates multiple instances by calling `create_vm_instance` in a loop, each with a unique name.

#### **Main Function to Run the Script**
```python
if __name__ == "__main__":
    PROJECT = input("Enter your Google Cloud Project ID: ")
    ZONE = input("Enter the zone (e.g., us-central1-a): ")
    INSTANCE_BASE_NAME = input("Enter the base name for the instances (e.g., proxy): ")
    NUM_INSTANCES = 100  # Set to 100 instances
    MACHINE_TYPE = input("Enter the machine type (e.g., f1-micro): ")
    IMAGE_FAMILY = input("Enter the image family (e.g., debian-10): ")
    IMAGE_PROJECT = input("Enter the image project (e.g., debian-cloud): ")
    
    STARTUP_SCRIPT = """#!/bin/bash
    sudo apt-get update
    sudo apt-get install -y squid
    sudo sed -i "s/http_access deny all/http_access allow all/" /etc/squid/squid.conf
    sudo systemctl restart squid
    """

    create_multiple_vms(PROJECT, ZONE, INSTANCE_BASE_NAME, NUM_INSTANCES, MACHINE_TYPE, IMAGE_FAMILY, IMAGE_PROJECT, STARTUP_SCRIPT)
```

- **User Inputs:** Prompts for project, zone, machine type, image family, and image project.
- **Create 100 Instances:** Calls the function to create 100 preemptible instances.

### **Step 4: Run the Script**
1. **Save the Script:** Save the Python script to a file, e.g., `create_vms.py`.
2. **Run the Script:** Execute the script in your terminal:
   ```bash
   python create_vms.py
   ```

3. **Enter the Required Information:** When prompted, provide your Google Cloud Project ID, zone, machine type (e.g., `f1-micro`), image family (e.g., `debian-10`), and image project (e.g., `debian-cloud`).

4. **Monitor Creation:** The script will output messages indicating the progress of instance creation.

### **Step 5: Verification**
- **Google Cloud Console:** After the script completes, you can verify that the instances were created by visiting the Compute Engine section in the Google Cloud Console.
- **Check IP Addresses:** Ensure that each instance has a unique external IP address.

### **Conclusion:**
This script will create 100 preemptible VM instances on Google Cloud, each with a unique external IP address. Preemptible instances are cost-effective, which fits within your $300 budget for 2 months, but be aware that they can be terminated by Google at any time.
