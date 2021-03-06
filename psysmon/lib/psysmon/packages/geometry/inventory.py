# LICENSE
#
# This file is part of pSysmon.
#
# If you use pSysmon in any program or publication, please inform and
# acknowledge its author Stefan Mertl (stefan@mertl-research.at).
#
# pSysmon is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
The inventory module.

:copyright:
    Stefan Mertl

:license:
    GNU General Public License, Version 3 
    http://www.gnu.org/licenses/gpl-3.0.html

This module contains the classed needed to build a pSysmon geometry 
inventory.
'''

import itertools
import psysmon
from obspy.core.utcdatetime import UTCDateTime
from psysmon.core.error import PsysmonError
from mpl_toolkits.basemap import pyproj
import warnings
import logging
from wx.lib.pubsub import setupkwargs
from wx.lib.pubsub import pub
from operator import attrgetter

class Inventory(object):

    def __init__(self, name, type = None):
        ''' Initialize the instance.

        Parameters
        ----------
        name : String
            The name of the inventory.

        type : String
            The type of the inventory.
        '''

        # The logger.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        ## The name of the inventory.
        self.name = name

        ## The type of the inventory.
        #
        # Based on the source the inventory can be of the following types:
        # - xml
        # - db
        # - manual
        self.type = type

        ## The recorders contained in the inventory.
        self.recorders = []

        ## The sensors contained in the inventory.
        self.sensors = []

        ## The networks contained in the inventory.
        self.networks = []


    def __str__(self):
        ''' Print the string representation of the inventory.
        '''
        out = "Inventory %s of type %s\n" % (self.name, self.type) 

        # Print the networks.
        out =  out + str(len(self.networks)) + " network(s) in the inventory:\n"
        out = out + "\n".join([net.__str__() for net in self.networks])

        # Print the recorders.
        out = out + '\n\n'
        out =  out + str(len(self.recorders)) + " recorder(s) in the inventory:\n"
        out = out + "\n".join([rec.__str__() for rec in self.recorders])

        return out



    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['name', 'type', 'recorders', 'networks'] 
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False


    def add_recorder(self, recorder):
        ''' Add a recorder to the inventory.

        Parameters
        ----------
        recorder : :class:`Recorder`
            The recorder to add to the inventory.
        '''
        added_recorder = None

        if not self.get_recorder(serial = recorder.serial):
            self.recorders.append(recorder)
            recorder.parent_inventory = self
            added_recorder = recorder
        else:
            self.logger.warning('The recorder with serial %s already exists in the inventory.',
                    recorder.serial)

        return added_recorder


    def remove_recorder_by_instance(self, recorder):
        ''' Remove a recorder from the inventory.
        '''
        if recorder in self.recorders:
            self.recorders.remove(recorder)



    def add_station(self, network_name, station_to_add):
        ''' Add a station to the inventory.

        Parameters
        ----------
        network_name : String
            The name of the network to which to add the station.

        station_to_add : :class:`Station`
            The station to add to the inventory.
        '''
        added_station = None

        # If the network is found in the inventory, add it to the network.
        cur_net = self.get_network(name = network_name)
        if len(cur_net) == 1:
            cur_net = cur_net[0]
            added_station = cur_net.add_station(station_to_add)
        elif len(cur_net) > 1:
            self.logger.error("Multiple networks found with the same name. Don't know how to proceed.")
        else:
            self.logger.error("The network %s of station %s doesn't exist in the inventory.\n", network_name, station_to_add.name)

        return added_station



    def remove_station(self, snl):
        ''' Remove a station from the inventory.

        Parameters
        ----------
        scnl : tuple (String, String, String)
            The SNL code of the station to remove from the inventory.
        '''
        removed_station = None

        cur_net = self.get_network(name = snl[1])

        if cur_net:
            if len(cur_net) == 1:
                cur_net = cur_net[0]
                removed_station = cur_net.remove_station(name = snl[0], location = snl[2])
            else:
                self.logger.error('More than one networks with name %s where found in the inventory.', snl[1])
        return removed_station



    def add_sensor(self, sensor_to_add):
        ''' Add a sensor to the inventory.

        Parameters
        ----------
        sensor_to_add : :class:`Sensor`
            The sensor to add to the inventory.
        '''
        added_sensor = None
        if not self.get_sensor(serial = sensor_to_add.serial):
            self.sensors.append(sensor_to_add)
            sensor_to_add.parent_inventory = self
            added_sensor = sensor_to_add
        else:
            self.logger.warning('The sensor with serial %s already exists in the inventory.',
                    sensor_to_add.serial)

        return added_sensor


    def remove_sensor_by_instance(self, sensor_to_remove):
        ''' Remove a sensor from the inventory.

        Parameters
        ----------
        sensor_to_remove : :class:`Sensor`
            The sensor to remove from the inventory.
        '''
        if sensor_to_remove in self.sensors:
            self.sensors.remove(sensor_to_remove)


    def add_network(self, network):
        ''' Add a new network to the database inventory.

        Parameters
        ----------
        network : :class:`Network`
            The network to add to the database inventory.
        '''
        added_network = None

        if not self.get_network(name = network.name):
            self.networks.append(network)
            network.parent_inventory = self
            added_network = network
        else:
            self.logger.warning('The network %s already exists in the inventory.', network.name)

        return added_network

    def remove_network_by_instance(self, network_to_remove):
        ''' Remove a network instance from the inventory.
        '''
        if network_to_remove in self.networks:
            self.networks.remove(network_to_remove)


    def remove_network(self, name):
        ''' Remove a network from the inventory.

        Parameters
        ----------
        name : String
            The name of the network to remove.
        '''
        removed_network = None

        net_2_remove = [x for x in self.networks if x.name == name]

        if len(net_2_remove) == 1:
            self.networks.remove(net_2_remove[0])
            removed_network = net_2_remove[0]
        else:
            # This shouldn't happen.
            self.logger.error('Found more than one network with the name %s.', name)

        return removed_network


    def has_changed(self):
        ''' Check if any element in the inventory has been changed.
        '''
        for cur_sensor in self.sensors:
            if cur_sensor.has_changed is True:
                self.logger.debug('Sensor changed')
                return True

        for cur_recorder in self.recorders:
            if cur_recorder.has_changed is True:
                self.logger.debug('Recorder changed')
                return True

        for cur_network in self.networks:
            if cur_network.has_changed is True:
                self.logger.debug('Network changed.')
                return True

        return False


    ## Refresh the inventory networks.
    def refresh_networks(self):
        for cur_network in self.networks:
            cur_network.refresh_stations(self.stations)


    ## Refresh the inventory recorders.
    def refresh_recorders(self):
        for cur_recorder in self.recorders:
            cur_recorder.refresh_sensors()

        for cur_sensor in self.sensors:
            self.add_sensor(cur_sensor)


    ## Read the inventory from an XML file.
    def import_from_xml(self, filename):
        inventory_parser = InventoryXmlParser(self, filename)
        try:
            inventory_parser.parse()
        except PsysmonError as e:
            raise e

        self.type = 'xml'


    def get_recorder(self, **kwargs):
        ''' Get a recorder from the inventory.

        Parameters
        ----------
        serial : String
            The serial number of the recorder.

        model : String
            The recorder model.

        producer : String
            The recorder producer.

        Returns
        -------
        recorder : List of :class:'~Recorder'
            The recorder(s) in the inventory matching the search criteria.
        '''
        ret_recorder = self.recorders

        valid_keys = ['serial', 'model', 'producer']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_recorder = [x for x in ret_recorder if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_recorder


    def get_stream(self, **kwargs):
        ''' Get a stream of a recorder from the inventory.

        Parameters
        ----------
        serial : String
            The serial number of the recorder containing the stream.

        model : String
            The model of the recorder containing the stream.

        producer : String
            The producer of the recorder containing the stream.

        name : String
            The name of the component.
        '''
        ret_stream = list(itertools.chain.from_iterable([x.streams for x in self.recorders]))

        valid_keys = ['name', 'serial', 'model', 'producer']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_stream = [x for x in ret_stream if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_stream


    def get_sensor(self, **kwargs):
        ''' Get a sensor from the inventory.

        Parameters
        ----------
        serial : String
            The serial number of the sensor.

        model : String
            The model of the sensor.

        producer : String
            The producer of the sensor.

        label : String
            The label of the sensor
        '''
        ret_sensor = self.sensors

        valid_keys = ['serial', 'model', 'producer']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_sensor = [x for x in ret_sensor if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_sensor



    def get_component(self, **kwargs):
        ''' Get a component of a sensor from the inventory.

        Parameters
        ----------
        serial : String
            The serial number of the sensor containing the component.

        model : String
            The model of the sensor containing the component.

        producer : String
            The producer of the sensor containing the component.

        name : String
            The name of the component.
        '''
        ret_component = list(itertools.chain.from_iterable([x.components for x in self.sensors]))


        valid_keys = ['name', 'serial', 'model', 'producer']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_component = [x for x in ret_component if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_component




    def get_station(self, **kwargs):
        ''' Get a station from the inventory.

        Parameters
        ----------
        name : String
            The name (code) of the station.

        network : String
            The name of the network of the station.

        location : String
            The location code of the station.
        '''
        ret_station = list(itertools.chain.from_iterable([x.stations for x in self.networks]))

        valid_keys = ['name', 'network', 'location']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_station = [x for x in ret_station if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_station


    def get_channel(self, **kwargs):
        ''' Get a chennel from the inventory.

        Paramters
        ---------
        network : String
            The name of the network.

        station : String
            The name (code) of the station.

        station : String
            The location identifier.

        name : String
            The name of the channel.
        '''

        search_dict = {}
        if 'network' in kwargs.keys():
            search_dict['network'] = kwargs['network']
            kwargs.pop('network')

        if 'station' in kwargs.keys():
            search_dict['name'] = kwargs['station']
            kwargs.pop('station')

        if 'location' in kwargs.keys():
            search_dict['location'] = kwargs['location']
            kwargs.pop('location')

        stations = self.get_station(**search_dict)

        ret_channel = list(itertools.chain.from_iterable([x.channels for x in stations]))

        valid_keys = ['name',]

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_channel = [x for x in ret_channel if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)
        return ret_channel


    def get_channel_from_stream(self, start_time = None, end_time = None, **kwargs):
        ''' Get the channels to which a stream is assigned to.
        '''
        ret_channel = list(itertools.chain.from_iterable(x.channels for x in self.get_station()))

        ret_channel = [x for x in ret_channel if x.get_stream(start_time = start_time,
                                                              end_time = end_time,
                                                              **kwargs)]
        return ret_channel







    def get_network(self, **kwargs):
        ''' Get a network from the inventory.

        Parameters
        ----------
        name : String
            The name of the network.

        type : String
            The type of the network.
        '''
        ret_network = self.networks

        valid_keys = ['name', 'type']
        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_network = [x for x in ret_network if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_network


    @classmethod
    def from_db_inventory(cls, db_inventory):
        pass



class Recorder(object):
    ''' A seismic data recorder.
    '''

    def __init__(self, serial, model, producer, description = None, id=None, parent_inventory=None,
            author_uri = None, agency_uri = None, creation_time = None):
        ''' Initialize the instance.

        '''
        ## The recorder database id.
        self.id = id

        ## The recorder serial number.
        self.serial = str(serial)

        # The model name or number.
        self.model = model

        # The producer of the sensor.
        self.producer = producer

        # The description of the recorder.
        self.description = description

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # A list of Stream instances related to the recorder.
        self.streams = [];

        ## The parent inventory.
        self.parent_inventory = parent_inventory

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);


    def __str__(self):
        ''' Returns a readable representation of the Recorder instance.
        '''
        out = 'id:\t%s\nserial:\t%s\nmodel:\t%s\n%d sensor(s):\n' % (str(self.id), self.serial, self.model, len(self.sensors))
        return out


    def __setitem__(self, name, value):
        self.__dict__[name] = value
        self.has_changed = True 


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['id', 'serial', 'model', 'producer', 'description', 'has_changed',
                                  'streams']
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False



    def add_stream(self, cur_stream):
        ''' Add a stream to the recorder.

        Parameters
        ----------
        stream : :class:`Stream`
            The stream to add to the recorder.
        '''
        added_stream = None
        if cur_stream not in self.streams:
            self.streams.append(cur_stream)
            cur_stream.parent_recorder = self
            added_stream = cur_stream

        return added_stream


    def pop_stream_by_instance(self, stream):
        ''' Remove a component from the sensor using the component instance.
        '''
        removed_stream = None
        if not stream.assigned_channels:
            # If the stream is not assigned to a channel, remove it.
            if stream in self.streams:
                self.streams.remove(stream)
                removed_stream = stream

        return removed_stream


    def pop_stream(self, **kwargs):
        ''' Remove a stream from the recorder.

        Parameters
        ----------
        name : String
            The name of the stream.

        label : String
            The label of the stream.

        agency_uri : String
            The agency_uri of the stream.

        author_uri : string
            The author_uri of the stream.

        Returns
        -------
        streams_popped : List of :class:`Stream`
            The removed streams.
        '''
        streams_popped = []
        streams_to_pop = self.get_stream(**kwargs)

        for cur_stream in streams_to_pop:
            cur_stream.parent_recorder = None
            streams_popped.append(self.streams.pop(self.streams.index(cur_stream)))

        return streams_popped


    def get_stream(self, **kwargs):
        ''' Get a stream from the recorder.

        Parameters
        ----------
        name : String
            The name of the stream.

        label : String
            The label of the stream.

        agency_uri : String
            The agency_uri of the stream.

        author_uri : string
            The author_uri of the stream.
        '''
        ret_stream = self.streams

        valid_keys = ['name', 'label', 'agency_uri', 'author_uri']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_stream = [x for x in ret_stream if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_stream



class RecorderStream(object):
    ''' A digital stream of a data recorder.
    '''

    def __init__(self, name, label,
                 agency_uri = None, author_uri = None,
                 creation_time = None, parent_recorder = None):
        ''' Initialization of the instance.
        '''
        # The logging logger instance.
        logger_prefix = psysmon.logConfig['package_prefix']
        loggerName = logger_prefix + "." + __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(loggerName)

        # The name of the stream.
        self.name = name

        # The label of the stream.
        self.label = label

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

        # The parent recorder holding the stream.
        self.parent_recorder = parent_recorder

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # A list of :class: `TimeBox` instances holding the assigned
        # components.
        self.components = []

        # A list of :class: `RecorderStreamParameter` instances.
        self.parameters = []


    @property
    def parent_inventory(self):
        if self.parent_recorder is not None:
            return self.parent_recorder.parent_inventory
        else:
            return None


    @property
    def serial(self):
        if self.parent_recorder is not None:
            return self.parent_recorder.serial
        else:
            return None


    @property
    def model(self):
        if self.parent_recorder is not None:
            return self.parent_recorder.model
        else:
            return None

    @property
    def producer(self):
        if self.parent_recorder is not None:
            return self.parent_recorder.producer
        else:
            return None


    @property
    def assigned_channels(self):
        # The channels to which the stream is assigned to.
        assigned_channels = []
        station_list = self.parent_inventory.get_station()
        for cur_station in station_list:
            for cur_channel in cur_station.channels:
                if cur_channel.get_stream(serial = self.serial, name = self.name):
                    assigned_channels.append(cur_channel)
        return assigned_channels



    def __setitem__(self, name, value):
        self.__dict__[name] = value
        self.has_changed = True
        if self.parent_recorder is not None:
            self.parent_recorder.has_changed =  True

        # Send an inventory update event.
        msgTopic = 'inventory.update.stream'
        msg = (self, name, value)
        pub.sendMessage(msgTopic, msg)


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['name', 'label', 'gain',
                    'bitweight', 'bitweight_units', 'components', 'has_changed']
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False


    def add_component(self, serial, model, producer, name, start_time, end_time):
        ''' Add a sensor component to the stream.

        The component with specified serial and name is searched
        in the parent inventory and if available, the sensor is added to
        the stream for the specified time-span.

        Parameters
        ----------
        serial : String
            The serial number of the sensor which holds the component.

        model : String
            The model of the sensor which holds the component.

        producer : String
            The producer of the sensor which holds the component.

        name : String
            The name of the component.

        start_time : :class:`obspy.core.utcdatetime.UTCDateTime`
            The time from which on the sensor has been operating at the station.

        end_time : :class:`obspy.core.utcdatetime.UTCDateTime`
            The time up to which the sensor has been operating at the station. "None" if the station is still running.
        '''
        if self.parent_inventory is None:
            raise RuntimeError('The stream needs to be part of an inventory before a sensor can be added.')

        added_component = None
        cur_component = self.parent_inventory.get_component(serial = serial,
                                                            model = model,
                                                            producer = producer,
                                                            name = name)
        if not cur_component:
            msg = 'The specified component (serial = %s, name = %s) was not found in the inventory.' % (serial, name)
            raise RuntimeError(msg)
        elif len(cur_component) == 1:
            cur_component = cur_component[0]

            try:
                start_time = UTCDateTime(start_time)
            except:
                start_time = None

            try:
                end_time = UTCDateTime(end_time)
            except:
                end_time = None

            if self.get_component(start_time = start_time,
                                  end_time = end_time):
                # A sensor is already assigned to the stream for this timespan.
                if start_time is not None:
                    start_string = start_time.isoformat
                else:
                    start_string = 'big bang'

                if end_time is not None:
                    end_string = end_time.isoformat
                else:
                    end_string = 'running'

                msg = 'The component (serial: %s,  name: %s) is already deployed during the specified timespan from %s to %s.' % (serial, name, start_string, end_string)
                raise RuntimeError(msg)
            else:
                self.components.append(TimeBox(item = cur_component,
                                               start_time = start_time,
                                               end_time = end_time,
                                               parent = self))
                self.has_changed = True
                added_component = cur_component
        else:
            msg = "Got more than one component with serial=%s and name = %s. Only one component with a serial-component combination should be in the inventory. Don't know how to proceed." % (serial, name)
            raise RuntimeError(msg)

        return added_component


    def remove_component_by_instance(self, timebox):
        ''' Remove a component from the stream.

        '''
        if timebox in self.components:
            self.components.remove(timebox)


    def remove_parameter_by_instance(self, parameter):
        ''' Remove a parameter from the stream.
        '''
        if parameter in self.parameters:
            self.parameters.remove(parameter)


    def get_component(self, start_time = None, end_time = None, **kwargs):
        ''' Get a sensor from the stream.

        Parameters
        ----------
        name : String
            The name of the component.

        serial : String
            The serial of the sensor containing the component.

        start_time : :class:`~obspy.core.utcdatetime.UTCDateTime`
            The start time of the timespan to return.

        end_time : :class:`~obspy.core.utcdatetime.UTCDateTime`
            The end time of the timespan to return.

        '''
        ret_component = self.components

        valid_keys = ['serial', 'name']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_component = [x for x in ret_component if getattr(x.item, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        if start_time is not None:
            ret_component = [x for x in ret_component if (x.end_time is None) or (x.end_time > start_time)]

        if end_time is not None:
            ret_component = [x for x in ret_component if x.start_time < end_time]

        return ret_component


    def add_parameter(self, parameter_to_add):
        ''' Add a paramter to the recorder stream.

        Parameters
        ----------
        parameter_to_add : :class:`RecorderStreamParameter`
            The recorder stream parameter to add to the stream.
        '''
        added_parameter = None
        if not self.get_parameter(start_time = parameter_to_add.start_time,
                                  end_time = parameter_to_add.end_time):
            self.parameters.append(parameter_to_add)
            self.parameters = sorted(self.parameters, key = attrgetter('start_time'))
            parameter_to_add.parent_recorder_stream = self
            added_parameter = parameter_to_add
        else:
            raise RuntimeError('A parameter already exists for the given timespan.')

        return added_parameter


    def get_parameter(self, start_time = None, end_time = None):
        ''' Get parameter for a given timespan.

        '''
        ret_parameter = self.parameters

        if start_time is not None:
            start_time = UTCDateTime(start_time)
            ret_parameter = [x for x in ret_parameter if x.end_time is None or x.end_time > start_time]

        if end_time is not None:
            end_time = UTCDateTime(end_time)
            ret_parameter = [x for x in ret_parameter if x.start_time is None or x.start_time < end_time]

        return ret_parameter


    def get_free_parameter_slot(self, pos = 'both'):
        ''' Get a free time slot for a parameter.

        Parameters
        ----------
        pos : String
            The postion of the list of the next free time slot ('front', 'back', 'both').
        '''
        if self.parameters:
            last_parameter = sorted(self.parameters, key = attrgetter('start_time'))[-1]
            first_parameter = sorted(self.parameters, key = attrgetter('start_time'))[0]

            if pos == 'back':
                if last_parameter.end_time is None:
                    return None
                else:
                    return (last_parameter.end_time + 1, None)

            elif pos == 'front':
                if first_parameter.start_time is None:
                    return None
                else:
                    return (None, first_parameter.start_time - 1)
            elif pos == 'both':
                if last_parameter.end_time is None:
                    if first_parameter.start_time is None:
                        return None
                    else:
                        return (None, first_parameter.start_time - 1)
                else:
                    return (last_parameter.end_time + 1, None)
            else:
                raise ValueError('Use either back, front or both for the pos argument.')
        else:
            return (None, None)


    def get_free_component_slot(self, pos = 'both'):
        ''' Get a free time slot for a component.

        Parameters
        ----------
        pos : String
            The postion of the list of the next free time slot ('front', 'back', 'both').
        '''
        if self.components:
            last_component = sorted(self.components, key = attrgetter('start_time'))[-1]
            first_component = sorted(self.components, key = attrgetter('start_time'))[0]

            if pos == 'back':
                if last_component.end_time is None:
                    return None
                else:
                    return (last_component.end_time + 1, None)

            elif pos == 'front':
                if first_component.start_time is None:
                    return None
                else:
                    return (None, first_component.start_time - 1)
            elif pos == 'both':
                if last_component.end_time is None:
                    if first_component.start_time is None:
                        return None
                    else:
                        return (None, first_component.start_time - 1)
                else:
                    return (last_component.end_time + 1, None)
            else:
                raise ValueError('Use either back, front or both for the pos argument.')
        else:
            return (None, None)


class RecorderStreamParameter(object):
    ''' Parameters of a recorder stream.
    '''

    def __init__(self, start_time, end_time = None,
                 gain = None, bitweight = None,
                 agency_uri = None, author_uri = None, creation_time = None,
                 parent_recorder_stream = None):
        ''' Initialize the instance.
        '''
        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The gain of the stream.
        try:
            self.gain = float(gain)
        except:
            self.gain = None

        # The bitweight of the stream.
        try:
            self.bitweight = float(bitweight)
        except:
            self.bitweight = None

        # The start time from which on the parameters were valid.
        try:
            self.start_time = UTCDateTime(start_time)
        except:
            self.start_time = None

        # The end time until which the parameters were valid.
        try:
            self.end_time = UTCDateTime(end_time)
        except:
            self.end_time = None

        # The recorder stream for which the parameters were set.
        self.parent_recorder_stream = parent_recorder_stream

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

        # Indicates if the attributes have been changed.
        self.has_changed = False


    @property
    def parent_inventory(self):
        if self.parent_recorder_stream is not None:
            return self.parent_recorder_stream.parent_inventory
        else:
            return None


    @property
    def start_time_string(self):
        if self.start_time is None:
            return 'big bang'
        else:
            return self.start_time.isoformat()


    @property
    def end_time_string(self):
        if self.end_time is None:
            return 'running'
        else:
            return self.end_time.isoformat()





class Sensor(object):
    ''' A seismic sensor.

    '''

    def __init__(self, serial, model, producer, description = None,
                 author_uri = None, agency_uri = None,
                 creation_time = None, parent_inventory = None):
        ''' Initialize the instance

        '''
        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The serial number of the sensor.
        self.serial = str(serial)

        # The model name or number.
        self.model = model

        # The producer of the sensor.
        self.producer = producer

        # A description of the sensor.
        self.description = description

        # The components of the sensor.
        self.components = []

        # The inventory containing this sensor.
        self.parent_inventory = parent_inventory

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

        # Indicates if the attributes have been changed.
        self.has_changed = False


    def __setitem__(self, name, value):
        self.__dict__[name] = value
        self.has_changed = True


    def add_component(self, component_to_add):
        ''' Add a component to the sensor.

        Parameters
        ----------
        component_to_add : :class:`SensorComponent`
            The component to add to the sensor.
        '''
        added_component = None
        if component_to_add not in self.components:
            self.components.append(component_to_add)
            component_to_add.parent_sensor = self
            added_component = component_to_add

        return added_component


    def get_component(self, **kwargs):
        ''' Get a component from the sensor.

        Parameters
        ----------
        name : String
            The name of the component.

        agency_uri : String
            The agency_uri of the component.

        author_uri : string
            The author_uri of the component.
        '''
        ret_component = self.components

        valid_keys = ['name', 'agency_uri', 'author_uri']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_component = [x for x in ret_component if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_component


    def pop_component_by_instance(self, component):
        ''' Remove a component from the sensor using the component instance.
        '''
        removed_component = None
        if not component.assigned_streams:
            # If the component is not assigned to a stream, remove it.
            if component in self.components:
                self.components.remove(component)
                removed_component = component

        return removed_component


    def pop_component(self, **kwargs):
        ''' Remove a component from the sensor.

        Parameters
        ----------
        name : String
            The name of the component.

        agency_uri : String
            The agency_uri of the component.

        author_uri : string
            The author_uri of the component.

        Returns
        -------
        components_popped : List of :class:`SensorComponent`
            The removed components.
        '''
        components_popped = []
        components_to_pop = self.get_component(**kwargs)

        for cur_component in components_to_pop:
            cur_component.parent_recorder = None
            components_popped.append(self.components.pop(self.components.index(cur_component)))

        return components_popped



class SensorComponent(object):
    ''' A component of a seismic sensor.
    '''

    def __init__(self, name, description = None,
                 input_unit = None, output_unit = None, deliver_unit = None,
                 author_uri = None, agency_uri = None, creation_time = None,
                 parent_sensor = None):
        ''' Initialize the instance.

        '''
        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The name of the component.
        self.name = name

        # The description.
        self.description = description

        # The unit of the parameter measured by the sensor (e.g. m).
        self.input_unit = input_unit

        # The unit to which the input unit is transformed by the sensor (e.g.
        # m/s).
        self.output_unit = output_unit

        # The unit of the measureable signal which is proportional to the
        # output unit (e.g. V).
        self.deliver_unit = deliver_unit

        ## The component parameters.
        self.parameters = []

        # The inventory containing this sensor.
        self.parent_sensor = parent_sensor

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

    @property
    def parent_inventory(self):
        if self.parent_sensor is not None:
            return self.parent_sensor.parent_inventory
        else:
            return None

    @property
    def serial(self):
        if self.parent_sensor is not None:
            return self.parent_sensor.serial
        else:
            return None

    @property
    def model(self):
        if self.parent_sensor is not None:
            return self.parent_sensor.model
        else:
            return None

    @property
    def producer(self):
        if self.parent_sensor is not None:
            return self.parent_sensor.producer
        else:
            return None



    @property
    def assigned_streams(self):
        # Check if the component is assigned to a recorder stream.
        assigned_streams = []
        recorder_list = self.parent_inventory.get_recorder()
        for cur_recorder in recorder_list:
            stream_list = cur_recorder.get_stream()
            for cur_stream in stream_list:
                if cur_stream.get_component(serial = self.serial,
                                            name = self.name):
                    assigned_streams.append(cur_stream)
        return assigned_streams


    def __setitem__(self, name, value):
        self.__dict__[name] = value
        self.has_changed = True
        self.logger.debug('Changing attribute %s of sensor %d', name, self.id)

        # Send an inventory update event.
        msgTopic = 'inventory.update.sensor'
        msg = (self, name, value)
        pub.sendMessage(msgTopic, msg)


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['name', 'description',
                                  'has_changed', 'parameters']
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False


    def add_parameter(self, parameter_to_add):
        ''' Add a sensor paramter instance to the sensor.

        Parameters
        ----------
        parameter_to_add : :class:`SensorParameter`
            The sensor parameter instance to be added.
        '''
        added_parameter = None
        if not self.get_parameter(start_time = parameter_to_add.start_time,
                                  end_time = parameter_to_add.end_time):
            self.parameters.append(parameter_to_add)
            parameter_to_add.parent_component = self
            added_parameter = parameter_to_add
        else:
            raise RuntimeError('A parameter already exists for the given timespan.')

        return added_parameter


    def remove_parameter(self, parameter_to_remove):
        ''' Remove a parameter from the component.
        '''
        self.parameters.remove(parameter_to_remove)



    def get_parameter(self, start_time = None, end_time = None):
        ''' Get a sensor from the recorder.

        Parameters
        ----------

        '''
        parameter = self.parameters

        if start_time is not None:
            start_time = UTCDateTime(start_time)
            parameter = [x for x in parameter if x.end_time is None or x.end_time > start_time]

        if end_time is not None:
            end_time = UTCDateTime(end_time)
            parameter = [x for x in parameter if x.start_time is None or x.start_time < end_time]

        return parameter



    def change_parameter_start_time(self, position, start_time):
        msg = ''    
        cur_row = self.parameters[position]

        if not isinstance(start_time, UTCDateTime):
            try:
                start_time = UTCDateTime(start_time)
            except:
                start_time = cur_row[1]
                msg = "The entered value is not a valid time."


        if not cur_row[2] or start_time < cur_row[2]:
            self.parameters[position] = (cur_row[0], start_time, cur_row[2])
            cur_row[0]['start_time'] = start_time
        else:
            start_time = cur_row[1]
            msg = "The start-time has to be smaller than the begin time."

        return (start_time, msg)


    def change_parameter_end_time(self, position, end_time):
        msg = ''    
        cur_row = self.parameters[position]

        if end_time == 'running':
            self.parameters[position] = (cur_row[0], cur_row[1], None)
            cur_row[0]['end_time'] = None
            return(end_time, msg)

        if not isinstance(end_time, UTCDateTime):
            try:
                end_time = UTCDateTime(end_time)
            except:
                end_time = cur_row[2]
                msg = "The entered value is not a valid time."


        if end_time:
            if not cur_row[1] or end_time > cur_row[1]:
                self.parameters[position] = (cur_row[0], cur_row[1], end_time)
                cur_row[0]['end_time'] = end_time
                # Send an inventory update event.
                #msgTopic = 'inventory.update.sensorParameterTime'
                #msg = (cur_row[0], 'time', (self, cur_row[0], cur_row[1], end_time))
                #pub.sendMessage(msgTopic, msg)
            else:
                end_time = cur_row[2]
                msg = "The end-time has to be larger than the begin time."

        return (end_time, msg)





## The sensor parameter class.
#
class SensorComponentParameter(object):
    ## The constructor.
    #
    # @param self The object pointer.
    def __init__(self, sensitivity,
                 start_time, end_time, tf_type=None,
                 tf_units=None, tf_normalization_factor=None,
                 tf_normalization_frequency=None, tf_poles = None, tf_zeros = None,
                 parent_component = None, author_uri = None,
                 agency_uri = None, creation_time = None):

        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        ## The sensor sensitivity.
        try:
            self.sensitivity = float(sensitivity)
        except:
            self.sensitivity = None

        ## The transfer function type.
        # - displacement
        # - velocity
        # - acceleration
        self.tf_type = tf_type

        ## The transfer function units.
        self.tf_units = tf_units

        ## The transfer function normalization factor.
        try:
            self.tf_normalization_factor = float(tf_normalization_factor)
        except:
            self.tf_normalization_factor = None

        ## The transfer function normalization factor frequency.
        try:
            self.tf_normalization_frequency = float(tf_normalization_frequency)
        except:
            self.tf_normalization_frequency = None

        ## The transfer function as PAZ.
        if tf_poles is None:
            tf_poles = []

        if tf_zeros is None:
            tf_zeros = []

        self.tf_poles = tf_poles
        self.tf_zeros = tf_zeros

        # The start_time from which the parameters are valid.
        try:
            self.start_time = UTCDateTime(start_time)
        except:
            self.start_time = None

        # The end time up to which the parameters are valid.
        try:
            self.end_time = UTCDateTime(end_time)
        except:
            self.end_time = None

        # The parent sensor holding the parameter.
        self.parent_component = parent_component

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

    @property
    def parent_inventory(self):
        if self.parent_component is not None:
            return self.parent_component.parent_inventory
        else:
            return None


    @property
    def start_time_string(self):
        if self.start_time is None:
            return 'big bang'
        else:
            return self.start_time.isoformat()


    @property
    def end_time_string(self):
        if self.end_time is None:
            return 'running'
        else:
            return self.end_time.isoformat()


    @property
    def zeros_string(self):
        zero_str = ''
        if self.tf_zeros:
            for cur_zero in self.tf_zeros:
                if zero_str == '':
                    zero_str = cur_zero.__str__()
                else:
                    zero_str = zero_str + ',' + cur_zero.__str__()

        return zero_str

    @property
    def poles_string(self):
        pole_str = ''
        if self.tf_poles:
            for cur_pole in self.tf_poles:
                if pole_str == '':
                    pole_str = cur_pole.__str__()
                else:
                    pole_str = pole_str + ',' + cur_pole.__str__()

        return pole_str


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['sensitivity', 'tf_type',
                                  'tf_units', 'tf_normalization_factor', 'tf_normalization_frequency',
                                  'id', 'tf_poles', 'tf_zeros', 'start_time', 'end_time',
                                  'has_changed']
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False


    def set_transfer_function(self, tf_type, tf_units, tf_normalization_factor, 
                            tf_normalization_frequency):
        ''' Set the transfer function parameters.

        '''
        self.tf_type = tf_type
        self.tf_units = tf_units
        self.tf_normalization_factor = tf_normalization_factor
        self.tf_normalization_frequency = tf_normalization_frequency


    def tf_add_complex_zero(self, zero):
        ''' Add a complex zero to the transfer function PAZ.

        '''
        self.logger.debug('Adding zero %s to parameter %s.', zero, self)
        self.logger.debug('len(self.tf_zeros): %s', len(self.tf_zeros))
        self.tf_zeros.append(zero)
        self.logger.debug('len(self.tf_zeros): %s', len(self.tf_zeros))

    def tf_add_complex_pole(self, pole):
        ''' Add a complec pole to the transfer function PAZ.

        '''
        self.tf_poles.append(pole)



## The station class.
#
class Station(object):

    ## The constructor.
    #
    # @param self The object pointer.
    def __init__(self, name, location, x, y, z,
            parent_network=None, coord_system=None, description=None, id=None,
            author_uri = None, agency_uri = None, creation_time = None):

        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        ## The station id.
        self.id = id

        ## The station name.
        self.name = name

        ## The station location.
        if location:
            self.location = str(location)
        else:
            self.location = '--'

        ## The station description.
        #
        # The extended name of the station.
        self.description = description

        ## The x coordinate of the station location.
        #
        # The coordinate system used is a right handed coordinate system with 
        # x pointing in the East direction, y pointing in the North direction and 
        # z pointing upwards.@n 
        # Depending on the coordinate system used x and y can also represent 
        # longitude and latitude.
        if x is None:
            raise ValueError("The x coordinate can't be None.")
        self.x = float(x)

        ## The y coordinate of the station location.
        #
        # The coordinate system used is a right handed coordinate system with 
        # x pointing in the East direction, y pointing in the North direction and 
        # z pointing upwards.@n 
        # Depending on the coordinate system used x and y can also represent 
        # longitude and latitude.
        if y is None:
            raise ValueError("The y coordinate can't be None.")
        self.y = float(y)

        ## The z coordinate of the station location.
        #
        # The coordinate system used is a right handed coordinate system with 
        # x pointing in the East direction, y pointing in the North direction and 
        # z pointing upwards.@n 
        # Depending on the coordinate system used x and y can also represent 
        # longitude and latitude.
        if z is None:
            raise ValueError("The z coordinate can't be None.")
        self.z = float(z)

        ## The coordinate system in which the x/y coordinates are given.
        # 
        # The coord_system string should be a valid EPSG code.@n 
        # See http://www.epsg-registry.org/ to find your EPSG code.
        self.coord_system = coord_system

        # A list of tuples of channels assigned to the station.
        self.channels = []

        # The network containing this station.
        self.parent_network = parent_network

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

    @property
    def network(self):
        if self.parent_network is not None:
            return self.parent_network.name
        else:
            return None

    @property
    def snl(self):
        return (self.name, self.network, self.location)

    @property
    def snl_string(self):
        return str.join(':', self.get_snl())

    @property
    def parent_inventory(self):
        if self.parent_network is not None:
            return self.parent_network.parent_inventory
        else:
            return None

    @property
    def location_string(self):
        if self.location is None:
            return '--'
        else:
            return self.location


    def __setitem__(self, name, value):
        self.logger.debug("Setting the %s attribute to %s.", name, value)
        self.__dict__[name] = value
        self.has_changed = True


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['id', 'name', 'location', 'description', 'x', 'y', 'z',
                                  'coord_system', 'channels', 'has_changed']
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    self.logger.error('Attribute %s not matching %s != %s.', cur_attribute, str(getattr(self, cur_attribute)), str(getattr(other, cur_attribute)))
                    return False

            return True
        else:
            return False


    def get_scnl(self):
        scnl = []
        for cur_sensor, start_time, end_time in self.sensors:
            cur_scnl = (self.name, cur_sensor.channel_name, self.network, self.location)
            if cur_scnl not in scnl:
                scnl.append(cur_scnl)

        return scnl


    def get_lon_lat(self):
        '''
        Return the coordinate system as WGS84 longitude latitude tuples.
        '''
        # TODO: Add a check for valid epsg string.

        dest_sys = "epsg:4326"

        if self.coord_system == dest_sys:
            return(self.x, self.y)

        src_proj = pyproj.Proj(init=self.coord_system)
        dst_proj = pyproj.Proj(init=dest_sys) 


        lon, lat = pyproj.transform(src_proj, dst_proj, self.x, self.y)
        self.logger.debug('Converting from "%s" to "%s"', src_proj.srs, dst_proj.srs)
        return (lon, lat)


    def add_channel(self, cur_channel):
        ''' Add a channel to the station

        Parameters
        ----------
        cur_channel : :class:`Channel`
            The channel to add to the station.
        '''
        added_channel = None
        if not self.get_channel(name = cur_channel.name):
            cur_channel.parent_station = self
            self.channels.append(cur_channel)
            self.has_changed = True
            added_channel = cur_channel

        return added_channel


    def remove_channel_by_instance(self, channel):
        ''' Remove a channel instance from the station.
        '''
        if channel in self.channels:
            self.channels.remove(channel)



    def get_channel(self, **kwargs):
        ''' Get a channel from the stream.

        Parameters
        ----------
        name : String
            The name of the channel.
        '''
        ret_channel = self.channels

        valid_keys = ['name']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_channel = [x for x in ret_channel if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_channel


    def get_unique_channel_names(self):
        channel_names = []

        for cur_channel, start, end in self.channels:
            if cur_channel.name not in channel_names:
                channel_names.append(cur_channel.name)

        return channel_names



class Channel(object):
    ''' A channel of a station.
    '''
    def __init__(self, name, description = None, id = None,
            agency_uri = None, author_uri = None, creation_time = None,
            parent_station = None):
        ''' Initialize the instance

        Parameters
        ----------
        name : String
            The name of the channel.

        streams : List of tuples.
            The streams assigned to the channel.

        '''
        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        # The database id of the channel.
        self.id = id

        # The name of the channel.
        self.name = name

        # The description of the channel.
        self.description = description

        # The streams assigned to the channel.
        self.streams = []

        # The station holding the channel.
        self.parent_station = parent_station

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # The author.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);

    @property
    def parent_inventory(self):
        if self.parent_station is not None:
            return self.parent_station.parent_inventory
        else:
            return None

    @property
    def scnl(self):
        if self.parent_station is not None:
            return (self.parent_station.name,
                    self.name,
                    self.parent_station.network,
                    self.parent_station.location)
        else:
            return None

    @property
    def scnl_string(self):
        return str.join(':', self.scnl)


    def add_stream(self, serial, model, producer, name, start_time, end_time):
        ''' Add a stream to the channel.

        Parameters
        ----------
        serial : String
            The serial number of the recorder containing the stream.

        model : String
            The model of the recorder containing the stream.

        producer : String
            The producer of the recorder containing the stream.

        name : String
            The name of the stream.

        start_time : :class:`obspy.core.utcdatetime.UTCDateTime`
            The time from which on the stream has been operating at the channel.

        end_time : :class:`obspy.core.utcdatetime.UTCDateTime`
            The time up to which the stream has been operating at the channel. "None" if the channel is still running.
        '''
        if self.parent_inventory is None:
            raise RuntimeError('The stream needs to be part of an inventory before a sensor can be added.')

        added_stream = None
        cur_stream = self.parent_inventory.get_stream(serial = serial,
                                                      model = model,
                                                      producer = producer,
                                                      name = name)

        if not cur_stream:
            self.logger.error('The specified stream (serial = %s, model = %s, producer = %s, name = %s) was not found in the inventory.',
                              serial, model, producer, name)
        elif len(cur_stream) == 1:
            cur_stream = cur_stream[0]

            try:
                start_time = UTCDateTime(start_time)
            except:
                start_time = None

            try:
                end_time = UTCDateTime(end_time)
            except:
                end_time = None

            if self.get_stream(serial = serial,
                               model = model,
                               producer = producer,
                               name = name,
                               start_time = start_time,
                               end_time = end_time):
                # The stream is already assigned to the station for this
                # time-span.
                if start_time is not None:
                    start_string = end_time.isoformat
                else:
                    start_string = 'big bang'

                if end_time is not None:
                    end_string = end_time.isoformat
                else:
                    end_string = 'running'

                self.logger.error('The stream (serial: %s,  name: %s) is already deployed during the specified timespan from %s to %s.', serial, name, start_string, end_string)
            else:
                self.streams.append(TimeBox(item = cur_stream,
                                            start_time = start_time,
                                            end_time = end_time,
                                            parent = self))
                self.has_changed = True
                added_stream = cur_stream

        return added_stream


    def remove_stream_by_instance(self, stream_timebox):
        ''' Remove a stream timebox.
        '''
        self.streams.remove(stream_timebox)


    def remove_stream(self, start_time = None, end_time = None, **kwargs):
        ''' Remove a stream from the channel.

        Parameters
        ----------
        '''
        stream_tb_to_remove = self.get_stream(start_time = start_time,
                                            end_time = end_time,
                                            **kwargs)

        for cur_stream_tb in stream_tb_to_remove:
            self.streams.remove(cur_stream_tb)


    def get_stream(self, start_time = None, end_time = None, **kwargs):
        ''' Get a stream from the channel.

        Parameters
        ----------
        serial : String
            The serial number of the recorder containing the stream.

        model : String
            The model of the recorder containing the stream.

        producer : String
            The producer of the recorder containing the stream.

        name : String
            The name of the stream.
        '''
        ret_stream = self.streams

        valid_keys = ['serial', 'model', 'producer', 'name']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_stream = [x for x in ret_stream if getattr(x.item, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        if start_time is not None:
            ret_stream = [x for x in ret_stream if (x.end_time is None) or (x.end_time >= start_time)]

        if end_time is not None:
            ret_stream = [x for x in ret_stream if x.start_time <= end_time]

        return ret_stream


    # TODO: Implement the methods to change the stream start- and end-time.
    # This will be analog to the sensors in the streams. It would be great to
    # have these methods in the TimeBox class.
    # Keep in mind, that in the DbInventory, the ORM mapper values of the 
    # time-spans have to be changed as well.


class Network(object):

    def __init__(self, name, description=None, type=None, author_uri = None,
            agency_uri = None, creation_time = None, parent_inventory=None):
        ''' Initialize the instance.
        '''
        # The logger instance.
        logger_name = __name__ + "." + self.__class__.__name__
        self.logger = logging.getLogger(logger_name)

        ## The parent inventory.
        self.parent_inventory = parent_inventory

        ## The network name (code).
        self.name = name

        ## The network description.
        self.description = description

        ## The network type.
        self.type = type

        ## The stations contained in the network.
        self.stations = []

        # Indicates if the attributes have been changed.
        self.has_changed = False

        # The author of the network.
        self.author_uri = author_uri

        # The agency of the author.
        self.agency_uri = agency_uri

        # The datetime of the creation.
        if creation_time == None:
            self.creation_time = UTCDateTime();
        else:
            self.creation_time = UTCDateTime(creation_time);


    def __setattr__(self, attr, value):
        ''' Control the attribute assignements.
        '''
        self.__dict__[attr] = value

        self.__dict__['has_changed'] = True


    def __eq__(self, other):
        if type(self) is type(other):
            compare_attributes = ['name', 'type', 'description', 'has_changed', 'stations'] 
            for cur_attribute in compare_attributes:
                if getattr(self, cur_attribute) != getattr(other, cur_attribute):
                    return False

            return True
        else:
            return False


    def add_station(self, station):
        ''' Add a station to the network.

        Parameters
        ----------
        station : :class:`Station`
            The station instance to add to the network.
        '''
        available_sl = [(x.name, x.location) for x in self.stations]
        if((station.name, station.location) not in available_sl):
            station.parent_network = self
            self.stations.append(station)
            return station
        else:
            self.logger.error("The station with SL code %s is already in the network.", x.name + ':' + x.location)
            return None


    def remove_station_by_instance(self, station_to_remove):
        ''' Remove a station instance from the network.
        '''
        if station_to_remove in self.stations:
            self.stations.remove(station_to_remove)


    def remove_station(self, name, location):
        ''' Remove a station from the network.

        Parameters
        ----------
        name : String
            The name of the station to remove.

        location : String
            The location of the station to remove.
        '''
        station_2_remove = [x for x in self.stations if x.name == name and x.location == location]

        removed_station = None
        if len(station_2_remove) == 0:
            removed_station = None
        elif len(station_2_remove) == 1:
            station_2_remove = station_2_remove[0]
            self.stations.remove(station_2_remove)
            station_2_remove.network = None
            station_2_remove.parent_network = None
            removed_station = station_2_remove
        else:
            # This shouldn't happen.
            self.logger.error('Found more than one network with the name %s.', name)
            return None

        return removed_station


    def get_station(self, **kwargs):
        ''' Get a station from the network.

        Parameters
        ----------
        name : String
            The name (code) of the station.

        location : String
            The location code of the station.

        id : Integer
            The database id of the station.

        snl : Tuple (station, network, location)
            The SNL tuple of the station.

        snl_string : String
            The SNL string in the format 'station:network:location'.
        '''
        ret_station = self.stations

        valid_keys = ['name', 'network', 'location', 'id', 'snl', 'snl_string']

        for cur_key, cur_value in kwargs.iteritems():
            if cur_key in valid_keys:
                ret_station = [x for x in ret_station if getattr(x, cur_key) == cur_value]
            else:
                warnings.warn('Search attribute %s is not existing.' % cur_key, RuntimeWarning)

        return ret_station




class TimeBox(object):
    ''' A container to hold an instance with an assigned time-span.

    '''

    def __init__(self, item, start_time, end_time = None, parent = None):
        ''' Initialize the instance.

        Parameters
        ----------

        '''
        # The instance holding the time-box.
        self.parent = parent

        # The item contained in the box.
        self.item = item

        # The start_time of the time-span.
        self.start_time = start_time

        # The end_time of the time-span.
        self.end_time = end_time


    def __eq__(self, other):
        is_equal = False
        try:
            if self.item is other.item:
                if self.start_time == other.start_time:
                    if self.end_time == other.end_time:
                        is_equal = True
        except:
            pass

        return is_equal


    def __getattr__(self, attr_name):
        return getattr(self.item, attr_name)


    @property
    def start_time_string(self):
        if self.start_time is None:
            return 'big bang'
        else:
            return self.start_time.isoformat()

    @property
    def end_time_string(self):
        if self.end_time is None:
            return 'running'
        else:
            return self.end_time.isoformat()

