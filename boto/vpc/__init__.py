# Copyright (c) 2009 Mitch Garnaat http://garnaat.org/
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish, dis-
# tribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the fol-
# lowing conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABIL-
# ITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHOR BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

"""
Represents a connection to the EC2 service.
"""

from boto.ec2.connection import EC2Connection
from boto.resultset import ResultSet
from boto.vpc.vpc import VPC, VPCAttribute
from boto.vpc.customergateway import CustomerGateway
from boto.vpc.routetable import RouteTable
from boto.vpc.internetgateway import InternetGateway
from boto.vpc.vpngateway import VpnGateway, Attachment
from boto.vpc.dhcpoptions import DhcpOptions
from boto.vpc.subnet import Subnet
from boto.vpc.vpnconnection import VpnConnection
from boto.ec2 import RegionData
from boto.regioninfo import RegionInfo

def regions(**kw_params):
    """
    Get all available regions for the EC2 service.
    You may pass any of the arguments accepted by the VPCConnection
    object's constructor as keyword arguments and they will be
    passed along to the VPCConnection object.

    :rtype: list
    :return: A list of :class:`boto.ec2.regioninfo.RegionInfo`
    """
    regions = []
    for region_name in RegionData:
        region = RegionInfo(name=region_name,
                            endpoint=RegionData[region_name],
                            connection_cls=VPCConnection)
        regions.append(region)
    regions.append(RegionInfo(name='us-gov-west-1',
                            endpoint=RegionData[region_name],
                            connection_cls=VPCConnection)
    )
    return regions


def connect_to_region(region_name, **kw_params):
    """
    Given a valid region name, return a
    :class:`boto.vpc.VPCConnection`.
    Any additional parameters after the region_name are passed on to
    the connect method of the region object.

    :type: str
    :param region_name: The name of the region to connect to.

    :rtype: :class:`boto.vpc.VPCConnection` or ``None``
    :return: A connection to the given region, or None if an invalid region
             name is given
    """
    for region in regions(**kw_params):
        if region.name == region_name:
            return region.connect(**kw_params)
    return None


class VPCConnection(EC2Connection):

    # VPC methods

    def get_all_vpcs(self, vpc_ids=None, filters=None):
        """
        Retrieve information about your VPCs.  You can filter results to
        return information only about those VPCs that match your search
        parameters.  Otherwise, all VPCs associated with your account
        are returned.

        :type vpc_ids: list
        :param vpc_ids: A list of strings with the desired VPC ID's

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
            consists of a filter key and a filter value.
            Possible filter keys are:

            * *state* - a list of states of the VPC (pending or available)
            * *cidrBlock* - a list CIDR blocks of the VPC
            * *dhcpOptionsId* - a list of IDs of a set of DHCP options

        :rtype: list
        :return: A list of :class:`boto.vpc.vpc.VPC`
        """
        params = {}
        if vpc_ids:
            self.build_list_params(params, vpc_ids, 'VpcId')
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeVpcs', params, [('item', VPC)])

    def create_vpc(self, cidr_block, availability_zone=None, description=None):
        """
        Create a new Virtual Private Cloud.

        :type cidr_block: str
        :param cidr_block: A valid CIDR block

        :rtype: The newly created VPC
        :return: A :class:`boto.vpc.vpc.VPC` object
        """
        params = {'CidrBlock' : cidr_block}
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        if description:
            params['Description'] = description
        return self.get_object('CreateVpc', params, VPC)

    def delete_vpc(self, vpc_id):
        """
        Delete a Virtual Private Cloud.

        :type vpc_id: str
        :param vpc_id: The ID of the vpc to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'VpcId': vpc_id}
        return self.get_status('DeleteVpc', params)

    # Route Tables

    def get_all_route_tables(self, route_table_ids=None, filters=None):
        """
        Retrieve information about your routing tables. You can filter results
        to return information only about those route tables that match your
        search parameters. Otherwise, all route tables associated with your
        account are returned.

        :type route_table_ids: list
        :param route_table_ids: A list of strings with the desired route table
                                IDs.

        :type filters: list of tuples
        :param filters: A list of tuples containing filters. Each tuple
                        consists of a filter key and a filter value.

        :rtype: list
        :return: A list of :class:`boto.vpc.routetable.RouteTable`
        """
        params = {}
        if route_table_ids:
            self.build_list_params(params, route_table_ids, "RouteTableId")
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeRouteTables', params,
                             [('item', RouteTable)])

    def associate_route_table(self, route_table_id, subnet_id):
        """
        Associates a route table with a specific subnet.

        :type route_table_id: str
        :param route_table_id: The ID of the route table to associate.

        :type subnet_id: str
        :param subnet_id: The ID of the subnet to associate with.

        :rtype: str
        :return: The ID of the association created
        """
        params = {
            'RouteTableId': route_table_id,
            'SubnetId': subnet_id
        }

        result = self.get_object('AssociateRouteTable', params, ResultSet)
        return result.associationId

    def disassociate_route_table(self, association_id):
        """
        Removes an association from a route table. This will cause all subnets
        that would've used this association to now use the main routing
        association instead.

        :type association_id: str
        :param association_id: The ID of the association to disassociate.

        :rtype: bool
        :return: True if successful
        """
        params = { 'AssociationId': association_id }
        return self.get_status('DisassociateRouteTable', params)

    def create_route_table(self, vpc_id):
        """
        Creates a new route table.

        :type vpc_id: str
        :param vpc_id: The VPC ID to associate this route table with.

        :rtype: The newly created route table
        :return: A :class:`boto.vpc.routetable.RouteTable` object
        """
        params = { 'VpcId': vpc_id }
        return self.get_object('CreateRouteTable', params, RouteTable)

    def delete_route_table(self, route_table_id):
        """
        Delete a route table.

        :type route_table_id: str
        :param route_table_id: The ID of the route table to delete.

        :rtype: bool
        :return: True if successful
        """
        params = { 'RouteTableId': route_table_id }
        return self.get_status('DeleteRouteTable', params)

    def create_route(self, route_table_id, destination_cidr_block,
                     gateway_id=None, instance_id=None):
        """
        Creates a new route in the route table within a VPC. The route's target
        can be either a gateway attached to the VPC or a NAT instance in the
        VPC.

        :type route_table_id: str
        :param route_table_id: The ID of the route table for the route.

        :type destination_cidr_block: str
        :param destination_cidr_block: The CIDR address block used for the
                                       destination match.

        :type gateway_id: str
        :param gateway_id: The ID of the gateway attached to your VPC.

        :type instance_id: str
        :param instance_id: The ID of a NAT instance in your VPC.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'RouteTableId': route_table_id,
            'DestinationCidrBlock': destination_cidr_block
        }

        if gateway_id is not None:
            params['GatewayId'] = gateway_id
        elif instance_id is not None:
            params['InstanceId'] = instance_id

        return self.get_status('CreateRoute', params)

    def replace_route(self, route_table_id, destination_cidr_block,
                     gateway_id=None, instance_id=None, interface_id=None):
        """
        Replaces an existing route within a route table in a VPC.

        :type route_table_id: str
        :param route_table_id: The ID of the route table for the route.

        :type destination_cidr_block: str
        :param destination_cidr_block: The CIDR address block used for the
                                       destination match.

        :type gateway_id: str
        :param gateway_id: The ID of the gateway attached to your VPC.

        :type instance_id: str
        :param instance_id: The ID of a NAT instance in your VPC.

        :type interface_id: str
        :param interface_id: Allows routing to network interface attachments.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'RouteTableId': route_table_id,
            'DestinationCidrBlock': destination_cidr_block
        }

        if gateway_id is not None:
            params['GatewayId'] = gateway_id
        elif instance_id is not None:
            params['InstanceId'] = instance_id
        elif interface_id is not None:
            params['NetworkInterfaceId'] = interface_id

        return self.get_status('ReplaceRoute', params)

    def delete_route(self, route_table_id, destination_cidr_block):
        """
        Deletes a route from a route table within a VPC.

        :type route_table_id: str
        :param route_table_id: The ID of the route table with the route.

        :type destination_cidr_block: str
        :param destination_cidr_block: The CIDR address block used for
                                       destination match.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'RouteTableId': route_table_id,
            'DestinationCidrBlock': destination_cidr_block
        }

        return self.get_status('DeleteRoute', params)

    # Internet Gateways

    def get_all_internet_gateways(self, internet_gateway_ids=None,
                                  filters=None):
        """
        Get a list of internet gateways. You can filter results to return information
        about only those gateways that you're interested in.

        :type internet_gateway_ids: list
        :param internet_gateway_ids: A list of strings with the desired gateway IDs.

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
        """
        params = {}

        if internet_gateway_ids:
            self.build_list_params(params, internet_gateway_ids,
                                   'InternetGatewayId')
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeInternetGateways', params,
                             [('item', InternetGateway)])

    def create_internet_gateway(self):
        """
        Creates an internet gateway for VPC.

        :rtype: Newly created internet gateway.
        :return: `boto.vpc.internetgateway.InternetGateway`
        """
        return self.get_object('CreateInternetGateway', {}, InternetGateway)

    def delete_internet_gateway(self, internet_gateway_id):
        """
        Deletes an internet gateway from the VPC.

        :type internet_gateway_id: str
        :param internet_gateway_id: The ID of the internet gateway to delete.

        :rtype: Bool
        :return: True if successful
        """
        params = { 'InternetGatewayId': internet_gateway_id }
        return self.get_status('DeleteInternetGateway', params)

    def attach_internet_gateway(self, internet_gateway_id, vpc_id):
        """
        Attach an internet gateway to a specific VPC.

        :type internet_gateway_id: str
        :param internet_gateway_id: The ID of the internet gateway to attach.

        :type vpc_id: str
        :param vpc_id: The ID of the VPC to attach to.

        :rtype: Bool
        :return: True if successful
        """
        params = {
            'InternetGatewayId': internet_gateway_id,
            'VpcId': vpc_id
        }

        return self.get_status('AttachInternetGateway', params)

    def detach_internet_gateway(self, internet_gateway_id, vpc_id):
        """
        Detach an internet gateway from a specific VPC.

        :type internet_gateway_id: str
        :param internet_gateway_id: The ID of the internet gateway to detach.

        :type vpc_id: str
        :param vpc_id: The ID of the VPC to attach to.

        :rtype: Bool
        :return: True if successful
        """
        params = {
            'InternetGatewayId': internet_gateway_id,
            'VpcId': vpc_id
        }

        return self.get_status('DetachInternetGateway', params)

    # Customer Gateways

    def get_all_customer_gateways(self, customer_gateway_ids=None,
                                  filters=None):
        """
        Retrieve information about your CustomerGateways.  You can filter
        results to return information only about those CustomerGateways that
        match your search parameters.  Otherwise, all CustomerGateways
        associated with your account are returned.

        :type customer_gateway_ids: list
        :param customer_gateway_ids: A list of strings with the desired
            CustomerGateway ID's.

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
                        Possible filter keys are:

                         - *state*, the state of the CustomerGateway
                           (pending,available,deleting,deleted)
                         - *type*, the type of customer gateway (ipsec.1)
                         - *ipAddress* the IP address of customer gateway's
                           internet-routable external inteface

        :rtype: list
        :return: A list of :class:`boto.vpc.customergateway.CustomerGateway`
        """
        params = {}
        if customer_gateway_ids:
            self.build_list_params(params, customer_gateway_ids,
                                   'CustomerGatewayId')
        if filters:
            self.build_filter_params(params, dict(filters))

        return self.get_list('DescribeCustomerGateways', params,
                             [('item', CustomerGateway)])

    def create_customer_gateway(self, type, ip_address, bgp_asn):
        """
        Create a new Customer Gateway

        :type type: str
        :param type: Type of VPN Connection.  Only valid value currently is 'ipsec.1'

        :type ip_address: str
        :param ip_address: Internet-routable IP address for customer's gateway.
                           Must be a static address.

        :type bgp_asn: str
        :param bgp_asn: Customer gateway's Border Gateway Protocol (BGP)
                        Autonomous System Number (ASN)

        :rtype: The newly created CustomerGateway
        :return: A :class:`boto.vpc.customergateway.CustomerGateway` object
        """
        params = {'Type' : type,
                  'IpAddress' : ip_address,
                  'BgpAsn' : bgp_asn}
        return self.get_object('CreateCustomerGateway', params, CustomerGateway)

    def delete_customer_gateway(self, customer_gateway_id):
        """
        Delete a Customer Gateway.

        :type customer_gateway_id: str
        :param customer_gateway_id: The ID of the customer_gateway to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'CustomerGatewayId': customer_gateway_id}
        return self.get_status('DeleteCustomerGateway', params)

    # VPN Gateways

    def get_all_vpn_gateways(self, vpn_gateway_ids=None, filters=None):
        """
        Retrieve information about your VpnGateways.  You can filter results to
        return information only about those VpnGateways that match your search
        parameters.  Otherwise, all VpnGateways associated with your account
        are returned.

        :type vpn_gateway_ids: list
        :param vpn_gateway_ids: A list of strings with the desired VpnGateway ID's

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
                        Possible filter keys are:

                        - *state*, a list of states of the VpnGateway
                          (pending,available,deleting,deleted)
                        - *type*, a list types of customer gateway (ipsec.1)
                        - *availabilityZone*, a list of  Availability zones the
                          VPN gateway is in.

        :rtype: list
        :return: A list of :class:`boto.vpc.customergateway.VpnGateway`
        """
        params = {}
        if vpn_gateway_ids:
            self.build_list_params(params, vpn_gateway_ids, 'VpnGatewayId')
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeVpnGateways', params,
                             [('item', VpnGateway)])

    def create_vpn_gateway(self, type, availability_zone=None):
        """
        Create a new Vpn Gateway

        :type type: str
        :param type: Type of VPN Connection.  Only valid value currently is 'ipsec.1'

        :type availability_zone: str
        :param availability_zone: The Availability Zone where you want the VPN gateway.

        :rtype: The newly created VpnGateway
        :return: A :class:`boto.vpc.vpngateway.VpnGateway` object
        """
        params = {'Type' : type}
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        return self.get_object('CreateVpnGateway', params, VpnGateway)

    def delete_vpn_gateway(self, vpn_gateway_id):
        """
        Delete a Vpn Gateway.

        :type vpn_gateway_id: str
        :param vpn_gateway_id: The ID of the vpn_gateway to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'VpnGatewayId': vpn_gateway_id}
        return self.get_status('DeleteVpnGateway', params)

    def attach_vpn_gateway(self, vpn_gateway_id, vpc_id):
        """
        Attaches a VPN gateway to a VPC.

        :type vpn_gateway_id: str
        :param vpn_gateway_id: The ID of the vpn_gateway to attach

        :type vpc_id: str
        :param vpc_id: The ID of the VPC you want to attach the gateway to.

        :rtype: An attachment
        :return: a :class:`boto.vpc.vpngateway.Attachment`
        """
        params = {'VpnGatewayId': vpn_gateway_id,
                  'VpcId' : vpc_id}
        return self.get_object('AttachVpnGateway', params, Attachment)

    # Subnets

    def get_all_subnets(self, subnet_ids=None, filters=None):
        """
        Retrieve information about your Subnets.  You can filter results to
        return information only about those Subnets that match your search
        parameters.  Otherwise, all Subnets associated with your account
        are returned.

        :type subnet_ids: list
        :param subnet_ids: A list of strings with the desired Subnet ID's

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
                        Possible filter keys are:

                        - *state*, a list of states of the Subnet
                          (pending,available)
                        - *vpcId*, a list of IDs of teh VPC the subnet is in.
                        - *cidrBlock*, a list of CIDR blocks of the subnet
                        - *availabilityZone*, list of the Availability Zones
                          the subnet is in.


        :rtype: list
        :return: A list of :class:`boto.vpc.subnet.Subnet`
        """
        params = {}
        if subnet_ids:
            self.build_list_params(params, subnet_ids, 'SubnetId')
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeSubnets', params, [('item', Subnet)])

    def create_subnet(self, vpc_id, cidr_block, availability_zone=None):
        """
        Create a new Subnet

        :type vpc_id: str
        :param vpc_id: The ID of the VPC where you want to create the subnet.

        :type cidr_block: str
        :param cidr_block: The CIDR block you want the subnet to cover.

        :type availability_zone: str
        :param availability_zone: The AZ you want the subnet in

        :rtype: The newly created Subnet
        :return: A :class:`boto.vpc.customergateway.Subnet` object
        """
        params = {'VpcId' : vpc_id,
                  'CidrBlock' : cidr_block}
        if availability_zone:
            params['AvailabilityZone'] = availability_zone
        return self.get_object('CreateSubnet', params, Subnet)

    def delete_subnet(self, subnet_id):
        """
        Delete a subnet.

        :type subnet_id: str
        :param subnet_id: The ID of the subnet to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'SubnetId': subnet_id}
        return self.get_status('DeleteSubnet', params)


    # DHCP Options

    def get_all_dhcp_options(self, dhcp_options_ids=None):
        """
        Retrieve information about your DhcpOptions.

        :type dhcp_options_ids: list
        :param dhcp_options_ids: A list of strings with the desired DhcpOption ID's

        :rtype: list
        :return: A list of :class:`boto.vpc.dhcpoptions.DhcpOptions`
        """
        params = {}
        if dhcp_options_ids:
            self.build_list_params(params, dhcp_options_ids, 'DhcpOptionsId')
        return self.get_list('DescribeDhcpOptions', params,
                             [('item', DhcpOptions)])

    def create_dhcp_options(self, domain_name=None, domain_name_servers=None,
                            ntp_servers=None, netbios_name_servers=None,
                            netbios_node_type=None):
        """
        Create a new DhcpOption

        This corresponds to
        http://docs.amazonwebservices.com/AWSEC2/latest/APIReference/ApiReference-query-CreateDhcpOptions.html

        :type domain_name: str
        :param domain_name: A domain name of your choice (for example,
            example.com)

        :type domain_name_servers: list of strings
        :param domain_name_servers: The IP address of a domain name server. You
            can specify up to four addresses.

        :type ntp_servers: list of strings
        :param ntp_servers: The IP address of a Network Time Protocol (NTP)
            server. You can specify up to four addresses.

        :type netbios_name_servers: list of strings
        :param netbios_name_servers: The IP address of a NetBIOS name server.
            You can specify up to four addresses.

        :type netbios_node_type: str
        :param netbios_node_type: The NetBIOS node type (1, 2, 4, or 8). For
            more information about the values, see RFC 2132. We recommend you
            only use 2 at this time (broadcast and multicast are currently not
            supported).

        :rtype: The newly created DhcpOption
        :return: A :class:`boto.vpc.customergateway.DhcpOption` object
        """

        key_counter = 1
        params = {}

        def insert_option(params, name, value):
            params['DhcpConfiguration.%d.Key' % (key_counter,)] = name
            if isinstance(value, (list, tuple)):
                for idx, value in enumerate(value, 1):
                    key_name = 'DhcpConfiguration.%d.Value.%d' % (
                        key_counter, idx)
                    params[key_name] = value
            else:
                key_name = 'DhcpConfiguration.%d.Value.1' % (key_counter,)
                params[key_name] = value

            return key_counter + 1

        if domain_name:
            key_counter = insert_option(params,
                'domain-name', domain_name)
        if domain_name_servers:
            key_counter = insert_option(params,
                'domain-name-servers', domain_name_servers)
        if ntp_servers:
            key_counter = insert_option(params,
                'ntp-servers', ntp_servers)
        if netbios_name_servers:
            key_counter = insert_option(params,
                'netbios-name-servers', netbios_name_servers)
        if netbios_node_type:
            key_counter = insert_option(params,
                'netbios-node-type', netbios_node_type)

        return self.get_object('CreateDhcpOptions', params, DhcpOptions)

    def delete_dhcp_options(self, dhcp_options_id):
        """
        Delete a DHCP Options

        :type dhcp_options_id: str
        :param dhcp_options_id: The ID of the DHCP Options to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'DhcpOptionsId': dhcp_options_id}
        return self.get_status('DeleteDhcpOptions', params)

    def associate_dhcp_options(self, dhcp_options_id, vpc_id):
        """
        Associate a set of Dhcp Options with a VPC.

        :type dhcp_options_id: str
        :param dhcp_options_id: The ID of the Dhcp Options

        :type vpc_id: str
        :param vpc_id: The ID of the VPC.

        :rtype: bool
        :return: True if successful
        """
        params = {'DhcpOptionsId': dhcp_options_id,
                  'VpcId' : vpc_id}
        return self.get_status('AssociateDhcpOptions', params)

    # VPN Connection

    def get_all_vpn_connections(self, vpn_connection_ids=None, filters=None):
        """
        Retrieve information about your VPN_CONNECTIONs.  You can filter results to
        return information only about those VPN_CONNECTIONs that match your search
        parameters.  Otherwise, all VPN_CONNECTIONs associated with your account
        are returned.

        :type vpn_connection_ids: list
        :param vpn_connection_ids: A list of strings with the desired VPN_CONNECTION ID's

        :type filters: list of tuples
        :param filters: A list of tuples containing filters.  Each tuple
                        consists of a filter key and a filter value.
                        Possible filter keys are:

                        - *state*, a list of states of the VPN_CONNECTION
                          pending,available,deleting,deleted
                        - *type*, a list of types of connection, currently 'ipsec.1'
                        - *customerGatewayId*, a list of IDs of the customer gateway
                          associated with the VPN
                        - *vpnGatewayId*, a list of IDs of the VPN gateway associated
                          with the VPN connection

        :rtype: list
        :return: A list of :class:`boto.vpn_connection.vpnconnection.VpnConnection`
        """
        params = {}
        if vpn_connection_ids:
            self.build_list_params(params, vpn_connection_ids,
                                   'Vpn_ConnectionId')
        if filters:
            self.build_filter_params(params, dict(filters))
        return self.get_list('DescribeVpnConnections', params,
                             [('item', VpnConnection)])

    def create_vpn_connection(self, type, customer_gateway_id, vpn_gateway_id):
        """
        Create a new VPN Connection.

        :type type: str
        :param type: The type of VPN Connection.  Currently only 'ipsec.1'
                     is supported

        :type customer_gateway_id: str
        :param customer_gateway_id: The ID of the customer gateway.

        :type vpn_gateway_id: str
        :param vpn_gateway_id: The ID of the VPN gateway.

        :rtype: The newly created VpnConnection
        :return: A :class:`boto.vpc.vpnconnection.VpnConnection` object
        """
        params = {'Type' : type,
                  'CustomerGatewayId' : customer_gateway_id,
                  'VpnGatewayId' : vpn_gateway_id}
        return self.get_object('CreateVpnConnection', params, VpnConnection)

    def delete_vpn_connection(self, vpn_connection_id):
        """
        Delete a VPN Connection.

        :type vpn_connection_id: str
        :param vpn_connection_id: The ID of the vpn_connection to be deleted.

        :rtype: bool
        :return: True if successful
        """
        params = {'VpnConnectionId': vpn_connection_id}
        return self.get_status('DeleteVpnConnection', params)

    def disable_vgw_route_propagation(self, route_table_id, gateway_id):
        """
        Disables a virtual private gateway (VGW) from propagating routes to the
        routing tables of an Amazon VPC.

        :type route_table_id: str
        :param route_table_id: The ID of the routing table.

        :type gateway_id: str
        :param gateway_id: The ID of the virtual private gateway.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'RouteTableId': route_table_id,
            'GatewayId': gateway_id,
        }
        self.get_status('DisableVgwRoutePropagation', params)

    def enable_vgw_route_propagation(self, route_table_id, gateway_id):
        """
        Enables a virtual private gateway (VGW) to propagate routes to the
        routing tables of an Amazon VPC.

        :type route_table_id: str
        :param route_table_id: The ID of the routing table.

        :type gateway_id: str
        :param gateway_id: The ID of the virtual private gateway.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'RouteTableId': route_table_id,
            'GatewayId': gateway_id,
        }
        self.get_status('EnableVgwRoutePropagation', params)

    def create_vpn_connection_route(self, destination_cidr_block,
                                    vpn_connection_id):
        """
        Creates a new static route associated with a VPN connection between an
        existing virtual private gateway and a VPN customer gateway. The static
        route allows traffic to be routed from the virtual private gateway to
        the VPN customer gateway.

        :type destination_cidr_block: str
        :param destination_cidr_block: The CIDR block associated with the local
            subnet of the customer data center.

        :type vpn_connection_id: str
        :param vpn_connection_id: The ID of the VPN connection.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'DestinationCidrBlock': destination_cidr_block,
            'VpnConnectionId': vpn_connection_id,
        }
        self.get_status('CreateVpnConnectionRoute', params)

    def delete_vpn_connection_route(self, destination_cidr_block,
                                    vpn_connection_id):
        """
        Deletes a static route associated with a VPN connection between an
        existing virtual private gateway and a VPN customer gateway. The static
        route allows traffic to be routed from the virtual private gateway to
        the VPN customer gateway.

        :type destination_cidr_block: str
        :param destination_cidr_block: The CIDR block associated with the local
            subnet of the customer data center.

        :type vpn_connection_id: str
        :param vpn_connection_id: The ID of the VPN connection.

        :rtype: bool
        :return: True if successful
        """
        params = {
            'DestinationCidrBlock': destination_cidr_block,
            'VpnConnectionId': vpn_connection_id,
        }
        self.get_status('DeleteVpnConnectionRoute', params)

    def get_vpc_attribute(self, vpc_id, attribute=None):
        """
        Gets an attribute from a VPC.

        :type vpc_id: string
        :param vpc_id: The Amazon id of the VPC

        :type attribute: string
        :param attribute: The attribute you need information about
                          Valid choices are:

                          * enableDnsSupport
                          * enableDnsHostnames

        :rtype: :class:`boto.vpc.VPCAttribute`
        :return: An VPCAttribute object representing the value of the
                 attribute requested
        """
        params = {
            'VpcId': vpc_id
        }
        if attribute is not None:
            params['Attribute'] = attribute
        return self.get_object('DescribeVpcAttribute', params,
                               VPCAttribute, verb='POST')

    def modify_vpc_attribute(self, vpc_id, attribute, value):
        """
        Modifies the specified attribute of the specified VPC.
        You can only modify one attribute at a time.

        :type vpc_id: string
        :param vpc_id: The Amazon id of the VPC

        :type attribute: string
        :param attribute: The attribute you wish to change.

                          * enableDnsSupport - Specifies whether the DNS server
                            provided by Amazon is enabled for the VPC
                          * enableDnsHostnames - Specifies whether DNS hostnames are
                            provided for the instances launched in this VPC. You can only
                            set this attribute to ``true`` if EnableDnsSupport
                            is also ``true``.

        """
        if attribute:
            if isinstance(value, bool):
                if value:
                    value = 'true'
                else:
                    value = 'false'
        params = {
            'VpcId': vpc_id,
            '%s.Value' % (attribute[0].upper() + attribute[1:]): value
        }
        return self.get_status('ModifyVpcAttribute', params)
