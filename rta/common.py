
from itertools import islice, chain, tee
import datetime
import calendar
import inspect
from pymongo.objectid import ObjectId
import pandas
import numpy
import os

def batch(iterable, size):
    sourceiter = iter(iterable)
    while True:
      batchiter = islice(sourceiter, size)  
      sizeiter, batchiter = tee( batchiter, 2)
      isize = len(list(sizeiter))
      if isize < size:
        raise StopIteration
      yield chain([ batchiter.next()], batchiter)

def filepath(cls):
  return inspect.getfile(cls.__class__)
  
def getClassName(cls):
  return cls.split('.')[-1:][0]

json = None
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        try:
            # Google Appengine offers simplejson via django
            from django.utils import simplejson as json
        except ImportError:
            json_available = False

class JSONEncoder(json.JSONEncoder):
    """Default implementation of :class:`json.JSONEncoder` which provides
    serialization for :class:`datetime.datetime` objects (to ISO 8601 format).

    .. versionadded:: 0.9

    """

    def default(self, obj):
        """Provides serialization for :class:`datetime.datetime` objects (in
        addition to the serialization provided by the default
        :class:`json.JSONEncoder` implementation).

        If `obj` is a :class:`datetime.datetime` object, this converts it into
        the corresponding ISO 8601 string representation.

        """
        if hasattr(obj, 'as_json'):
            return obj.as_json()    
        elif isinstance(obj, datetime.datetime):
            # this is for javascript series date utctime * 1000
            return calendar.timegm( obj.utctimetuple() ) * 1000
        elif isinstance( obj, pandas.Series):
            return obj.iteritems()
        elif isinstance( obj, pandas.DataFrame):
            return obj.iterrows()
        elif isinstance(obj, (numpy.ndarray, numpy.float64, numpy.int64) ):
            if len(obj.shape) == 0:
                return float(obj)
            else:
                return [float(x) for x in obj]
        elif isinstance(obj, ObjectId):
          return str(obj)
        else:
          return super(JSONEncoder, self).default(obj)

def padNans(res, index):
  # print res
  pivot = index.shape[0] - res.shape[0]
  return pandas.Series( 
      index = index,
      data = numpy.concatenate( [ numpy.zeros(pivot, 'int'), res ] ), 
  )
  


def pd2json(df):
  if isinstance(df, pandas.DataFrame):
    df.to_records().tolist()          
  elif isinstance( df, pandas.Series ) or isinstance( df, pandas.TimeSeries ):
    return list( df.iteritems() )
  elif isinstance(df, pandas.Index ):
    return df.tolist()
  else:
    return df

def getuid():
  import uuid
  return uuid.uuid4()
  
def _delta( X, end, start ):
    return 100 * abs( 1.0 * ( X[end] - X[start] ) / X[start] )


def _sr( X, cutoff = 5, delta = 2, lines = 5, range_limit = 70):
    indices  = _zigzag(X, cutoff)
    series   = X.take(indices)
    strength = numpy.zeros( series.shape, dtype = 'int')
    
    range_upper_limit = series[-1] + ( series[-1] * range_limit) / 100
    range_lower_limit = series[-1] - ( series[-1] * range_limit) / 100

    for idx, item in enumerate(series):
        upper_limit = item + ( item * delta) / 100
        lower_limit = item - ( item * delta) / 100
        if item <= range_upper_limit and item >= range_lower_limit:
            strength[ idx ] = 1
            for _idx, oneitem in enumerate(series):
                if idx > _idx:
                    if lower_limit <= oneitem and upper_limit >= oneitem:
                        strength[ idx ] += 1

    for idx, item in enumerate(series):
        upper_limit = item + ( item * delta) / 100
        lower_limit = item - ( item * delta) / 100
        for _idx, oneitem in enumerate(series):
            if idx > _idx:
                if lower_limit <= oneitem and upper_limit >= oneitem:
                    strength[ _idx ] = 0
    
    topidx          = numpy.argsort( strength )[-lines:]
    tkidx           = series.index[ topidx ]
    print numpy.take( strength, topidx  )
    print series[ tkidx ]
    return tkidx

def _zigzag( X, cutoff = 5 ):
    idx, indices = 0, [0]
    base = (0, X[0] )
    pivot = ( 0, X[0] )
    idx = 0
    pdelta = bdelta = None
    while idx < X.size:
        bdelta = _delta( X, idx, base[0] )
        pdelta = _delta( X, idx, pivot[0] )

        if pdelta >= cutoff:
           tolerance = ( idx - indices[-1] > 2) # the reversal takes sometime
           if ( abs( X[idx] - base[1] ) < abs( pivot[1] - base[1]) ) or \
              ( abs(X[idx] - pivot[1])  > abs( base[1] - pivot[1]) ):
                indices.append( pivot[0])
                base = pivot
                pivot = ( idx, X[idx] )
                idx -= 1


        if bdelta >= cutoff:
            if abs( X[idx] - base[1] ) > abs( pivot[1] - base[1]):
                pivot = ( idx, X[idx] )

        idx += 1
    
    indices.append(pivot[0])

    return numpy.unique(indices)

def web_not_found(error=None):
    from flask import jsonify
    message = {
            'status': 404,
            'message': 'Not Found: ' + request.url,
    }
    resp = jsonify(message)
    resp.status_code = 404

    return resp

class DictStore(dict):

    def __init__(self, filename, odict):
        self.filename = filename
        self.closed = False
        super(DictStore, self).__init__(odict)

    def require_group(self, key):
        if not self.has_key(key):
            self.__setitem__(key, dict())
        return self.__getitem__(key)

    @classmethod
    def open(cls, filename):
        data = {}
        if os.path.exists(filename):
            data = pickle.load(open(filename, 'rb'))
        return cls(filename, data)

    def close(self):
        self.flush()
        self.closed = True

    def flush(self):
        pickle.dump(self.items(), open(self.filename, 'wb+'), -1)
    
__all__ = [ 'batch', 'JSONEncoder', 'padNans', 'pd2json', '_zigzag', '_sr', 'DictStore' ]
