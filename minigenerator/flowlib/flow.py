import datetime
import json

"""
This module defines the flow object
"""

import ipaddress as ip
import requests

class Base(object):
    """
    Base class
    """
    def __init__(self, *args, **kwargs):
        pass

    def setSizeToInt(self, size):
        """" Converts the sizes string notation to the corresponding integer
        (in bytes).  Input size can be given with the following
        magnitudes: B, K, M and G.
        """
        if isinstance(size, int):
            return size
        if isinstance(size,float):
            return int(size)

        try:
            conversions = {'B': 1, 'K': 1e3, 'M': 1e6, 'G': 1e9}
            digits_list = range(48,58) + [ord(".")]
            magnitude = chr(sum([ord(x) if (ord(x) not in digits_list) else 0 for x in size]))
            digit = float(size[0:(size.index(magnitude))])
            magnitude = conversions[magnitude]
            return int(magnitude*digit)
        except:
            return 0

    def setSizeToStr(self, size):
        """Expects an integer representing number of bytes as input.
        """
        units = [('G', 1e9), ('M', 1e6), ('K', 1e3), ('B', 1)]
        string = "{0:.2f}"
        if not size:
            return string.format(size) + "B"
        for (unit, value) in units:
            q, r = divmod(size, value)
            if q > 0.0:

                val = float((q*value + r)/value)
                #print q,val
                string = string.format(val)
                string = string + unit
                return string


    def setTimeToInt(self, duration = '00:01:00'):
        """
        From time to seconds
        :param duration:
        :return:
        """
        if isinstance(duration,int):
            return duration
        ftr = [3600,60,1]

        return sum([a*b for a,b in zip(ftr, map(int,duration.split(':')))])



    def setTimeToStr(self, time =60):
        """Expects time in seconds as integer.
        """
        return str(datetime.timedelta(seconds=time))


class Flow(Base):
    """
    This class implements a flow object.
    """
    def __init__(self, src = "10.0.0.1",
                 dst = "10.0.1.1",
                 sport = 5000, dport = 5001, tos=0, proto="UDP", size = 0, rate=0,
                 start_time = "00:00:10", duration = '00:01:00', *args, **kwargs):

        super(Flow, self).__init__(*args, **kwargs)
        self.src = src
        self.dst = dst
        self.sport = sport
        self.dport = dport
        self.tos = tos
        self.proto = proto

        self.size = self.setSizeToInt(size)
        self.rate = self.setSizeToInt(rate)


        self.start_time = self.setTimeToInt(start_time)
        self.duration = self.setTimeToInt(duration)


    def __repr__(self):
        return "{0}:{1}->{2}:{3} , protocol: {7} rate:{5} duration:{4},start: {6}".format(self.src,self.sport,self.dst,self.dport,self.duration,self.rate,self.start_time,self.proto)


    def __copy__(self):
        src_c = type(self.src)(self.src)
        dst_c = type(self.dst)(self.dst)
        size_c = type(self.size)(self.size)
        rate_c = type(self.rate)(self.rate)
        dport_c = type(self.dport)(self.dport)
        sport_c = type(self.sport)(self.sport)
        tos_c = type(self.tos)(self.tos)
        proto_c = type(self.proto)(self.proto)
        time_c = type(self.start_time)(self.start_time)
        duration_c = type(self.duration)(self.duration)
        return Flow(src=src_c, dst=dst_c, sport=sport_c,
                    dport=dport_c, tos = tos_c, proto=proto_c,size=size_c, start_time=time_c,
                    duration=duration_c,rate=rate_c)

    def __str__(self):
        a = "Src: %s:%s, Dst: %s:%s, Size: %s, Rate: %s start_time: %s, Duration: %s"
        return a%(self.src, str(self.sport),
                  self.dst, str(self.dport),
                  self.setSizeToStr(self.size),
                  self.setSizeToStr(self.rate),
                  self.setTimeToStr(self.start_time),
                  self.setTimeToStr(self.duration))

    def __setitem__(self, key, value):
        if key not in ['src','dst','sport','dport','size','rate','start_time','duration',"tos","proto"]:
            raise KeyError

        else:
            if key == 'size:':
                self.__setattr__(key, self.setSizeToInt(value))
            elif key == "rate":
                self.__setattr__(key, self.setSizeToInt(value))
            elif key == 'start_time':
                self.__setattr__(key, self.setTimeToInt(value))
            elif key == "duration":
                self.__setattr__(key, self.setTimeToInt(value))
            else:
                self.__setattr__(key, value)


    def __getitem__(self, key):
        if key not in ['src','dst','sport','dport','size','rate','start_time','duration',"tos","proto"]:
            raise KeyError
        else:
            return self.__getattribute__(key)

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)


    def toDICT(self):

        return {"src": self.src, "dst": self.dst, "sport":
                self.sport, "dport": self.dport,"tos":self.tos,"proto":self.proto, "size": self.size,
                "start_time": self.start_time, "duration": self.duration,"rate":self.rate}

    def toJSON(self):
        """Returns the JSON-REST string that identifies this flow
        """

        return json.dumps(self.toDict())


