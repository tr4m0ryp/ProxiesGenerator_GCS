import time
import google.auth
from google.cloud import compute_v1
from google.auth.transport.requests import Request

def create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script):
    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.zone = f"projects/{project}/zones/{zone}"
    instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    # Set the instance to be preemptible
    scheduling = compute_v1.Scheduling()
    scheduling.preemptible = True
    instance.scheduling = scheduling

    # Configure the boot disk
    disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
    disk.initialize_params = initialize_params
    disk.boot = True
    disk.auto_delete = True
    disk.type_ = "PERSISTENT"

    instance.disks = [disk]

    # Configure the network interface
    network_interface = compute_v1.NetworkInterface()
    access_config = compute_v1.AccessConfig()
    access_config.name = "External NAT"
    access_config.type_ = "ONE_TO_ONE_NAT"
    access_config.network_tier = "PREMIUM"
    
    # Request an ephemeral external IP address
    network_interface.access_configs = [access_config]
    network_interface.name = "global/networks/default"
    instance.network_interfaces = [network_interface]

    # Configure metadata and startup script
    metadata = compute_v1.Metadata()
    items = [compute_v1.Items(
        key="startup-script",
        value=startup_script
    )]
    metadata.items = items
    instance.metadata = metadata

    # Create the VM instance
    operation = compute.insert(project=project, zone=zone, instance_resource=instance)
    print(f"Waiting for operation {operation.name} to finish...")
    wait_for_operation(project, zone, operation.name)

    # Get the instance details after creation
    instance_details = compute.get(project=project, zone=zone, instance=instance_name)
    return instance_details

def wait_for_operation(project, zone, operation_name):
    # Initialize the ZoneOperationsClient to handle the operation
    operation_client = compute_v1.ZoneOperationsClient()
    
    while True:
        result = operation_client.get(project=project, zone=zone, operation=operation_name)

        if result.error:
            raise Exception(result.error)
        if result.status == compute_v1.Operation.Status.DONE:
            print("Operation complete.")
            return

def create_multiple_vms(project, zone, instance_base_name, num_instances, machine_type, image_family, image_project, startup_script, batch_size=2):
    credentials, project_id = google.auth.default()
    compute = compute_v1.InstancesClient(credentials=credentials)
    
    proxy_list = []  # List to store proxy details

    for i in range(0, num_instances, batch_size):
        batch_instances = min(batch_size, num_instances - i)
        for j in range(batch_instances):
            instance_name = f"{instance_base_name}-{i+j+1}"
            instance_details = create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script)
            
            # Extract the external IP address and other relevant details
            external_ip = None
            for iface in instance_details.network_interfaces:
                for config in iface.access_configs:
                    if config.name == "External NAT":
                        external_ip = config.nat_i_p
            
            proxy_info = {
                "instance_name": instance_name,
                "external_ip": external_ip,
                "zone": zone,
                "machine_type": machine_type
            }
            
            proxy_list.append(proxy_info)

        print(f"Completed batch {i // batch_size + 1}")

        # Add a delay to avoid hitting the quota limit
        time.sleep(60)  # Sleep for 60 seconds between batches (adjust as necessary)

    return proxy_list

if __name__ == "__main__":
    # User input for configuration settings
    PROJECT = input("Enter your Google Cloud Project ID: ")
    ZONE = input("Enter the zone (e.g., us-central1-a): ")
    INSTANCE_BASE_NAME = input("Enter the base name for the instances (e.g., proxy): ")
    NUM_INSTANCES = 100  # Set to 100 instances
    MACHINE_TYPE = input("Enter the machine type (e.g., f1-micro): ")
    IMAGE_FAMILY = "debian-11"  # Updated to use Debian 11
    IMAGE_PROJECT = "debian-cloud"
    
    # Optional: Customize this startup script or ask for user input if you want to adjust it
    STARTUP_SCRIPT = """#!/bin/bash
    sudo apt-get update
    sudo apt-get install -y squid
    sudo sed -i "s/http_access deny all/http_access allow all/" /etc/squid/squid.conf
    sudo systemctl restart squid
    """

    # Create multiple VMs and get the list of proxies
    proxy_list = create_multiple_vms(PROJECT, ZONE, INSTANCE_BASE_NAME, NUM_INSTANCES, MACHINE_TYPE, IMAGE_FAMILY, IMAGE_PROJECT, STARTUP_SCRIPT, batch_size=2)

    # Print the list of proxies with details
    print("Proxy Instances and Details:")
    for proxy in proxy_list:
        print(f"Instance Name: {proxy['instance_name']}, External IP: {proxy['external_ip']}, Zone: {proxy['zone']}, Machine Type: {proxy['machine_type']}")
