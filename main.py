import google.auth
from google.cloud import compute_v1
from google.auth.transport.requests import Request

def create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script):
    instance = compute_v1.Instance()
    instance.name = instance_name
    instance.zone = zone
    instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

    # Set the instance to be preemptible
    scheduling = compute_v1.Scheduling()
    scheduling.preemptible = True
    instance.scheduling = scheduling

    disk = compute_v1.AttachedDisk()
    initialize_params = compute_v1.AttachedDiskInitializeParams()
    initialize_params.source_image = f"projects/{image_project}/global/images/family/{image_family}"
    disk.initialize_params = initialize_params
    disk.boot = True
    disk.auto_delete = True
    disk.type_ = compute_v1.AttachedDisk.Type.PERSISTENT
    instance.disks = [disk]

    network_interface = compute_v1.NetworkInterface()
    access_config = compute_v1.AccessConfig()
    access_config.name = "External NAT"
    access_config.type_ = compute_v1.AccessConfig.Type.ONE_TO_ONE_NAT
    access_config.network_tier = "PREMIUM"
    
    # Request an ephemeral external IP address
    network_interface.access_configs = [access_config]
    network_interface.name = "global/networks/default"
    instance.network_interfaces = [network_interface]

    metadata = compute_v1.Metadata()
    items = [compute_v1.Items(
        key="startup-script",
        value=startup_script
    )]
    metadata.items = items
    instance.metadata = metadata

    operation = compute.insert(project=project, zone=zone, instance_resource=instance)
    print(f"Waiting for operation {operation.name} to finish...")
    wait_for_operation(compute, project, zone, operation.name)

    # Get the instance details after creation
    instance_details = compute.get(project=project, zone=zone, instance=instance_name)
    return instance_details

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

def create_multiple_vms(project, zone, instance_base_name, num_instances, machine_type, image_family, image_project, startup_script):
    credentials, project_id = google.auth.default()
    compute = compute_v1.InstancesClient(credentials=credentials)
    
    proxy_list = []  # List to store proxy details

    for i in range(1, num_instances + 1):
        instance_name = f"{instance_base_name}-{i}"
        instance_details = create_vm_instance(compute, project, zone, instance_name, machine_type, image_family, image_project, startup_script)
        
        # Extract the external IP address and other relevant details
        external_ip = None
        for iface in instance_details.network_interfaces:
            for config in iface.access_configs:
                if config.name == "External NAT":
                    external_ip = config.nat_ip
        
        proxy_info = {
            "instance_name": instance_name,
            "external_ip": external_ip,
            "zone": zone,
            "machine_type": machine_type
        }
        
        proxy_list.append(proxy_info)

    return proxy_list

if __name__ == "__main__":
    # User input for configuration settings
    PROJECT = input("Enter your Google Cloud Project ID: ")
    ZONE = input("Enter the zone (e.g., us-central1-a): ")
    INSTANCE_BASE_NAME = input("Enter the base name for the instances (e.g., proxy): ")
    NUM_INSTANCES = 100  # Set to 100 instances
    MACHINE_TYPE = input("Enter the machine type (e.g., f1-micro): ")
    IMAGE_FAMILY = input("Enter the image family (e.g., debian-10): ")
    IMAGE_PROJECT = input("Enter the image project (e.g., debian-cloud): ")
    
    # Optional: Customize this startup script or ask for user input if you want to adjust it
    STARTUP_SCRIPT = """#!/bin/bash
    sudo apt-get update
    sudo apt-get install -y squid
    sudo sed -i "s/http_access deny all/http_access allow all/" /etc/squid/squid.conf
    sudo systemctl restart squid
    """

    # Create multiple VMs and get the list of proxies
    proxy_list = create_multiple_vms(PROJECT, ZONE, INSTANCE_BASE_NAME, NUM_INSTANCES, MACHINE_TYPE, IMAGE_FAMILY, IMAGE_PROJECT, STARTUP_SCRIPT)

    # Print the list of proxies with details
    print("Proxy Instances and Details:")
    for proxy in proxy_list:
        print(f"Instance Name: {proxy['instance_name']}, External IP: {proxy['external_ip']}, Zone: {proxy['zone']}, Machine Type: {proxy['machine_type']}")
