from textwrap import dedent
import scipy.signal
import numpy as np

class IIRfilter(object):
    """ IIR Filter object to pre-filtering
    
    This class allows for the generation of various IIR filters
	in order to apply different frequency weighting to audio data
	before measuring the loudness. 
    Parameters
    ----------
    G : float
        Gain of the filter in dB.
    Q : float
        Q of the filter.
    fc : float
        Center frequency of the shelf in Hz.
    rate : float
        Sampling rate in Hz.
    filter_type: str
        Shape of the filter.
    """

    def __init__(self, G, Q, fc, rate, filter_type, passband_gain=1.0, n_channels=1):
        self.__G  = G
        self.__Q  = Q
        self.__fc = fc
        self.__rate = rate
        self.__filter_type = filter_type

        # calculate biquad coefficients
        self.generate_coefficients()

        self.n_channels = n_channels
        self.passband_gain = passband_gain

    def __str__(self):
        filter_info = dedent("""
        ------------------------------
        type: {type}
        ------------------------------
        Gain          = {G} dB
        Q factor      = {Q} 
        Center freq.  = {fc} Hz
        Sample rate   = {rate} Hz
        Passband gain = {passband_gain} dB
        ------------------------------
        b0 = {_b0}
        b1 = {_b1}
        b2 = {_b2}
        a0 = {_a0}
        a1 = {_a1}
        a2 = {_a2}
        ------------------------------
        """.format(type = self.filter_type, 
        G=self.G, Q=self.Q, fc=self.fc, rate=self.rate,
        passband_gain=self.passband_gain, 
        _b0=self.b[0], _b1=self.b[1], _b2=self.b[2], 
        _a0=self.a[0], _a1=self.a[1], _a2=self.a[2]))

        return filter_info

    def reset_state(self):
        if self.n_channels == 1:
            self.zi = np.zeros((max(len(self.a), len(self.b)) - 1,))
        else:
            self.zi = np.zeros((max(len(self.a), len(self.b)) - 1, self.n_channels))

    def generate_coefficients(self):
        """ Generates biquad filter coefficients using instance filter parameters. 
        This method is called whenever an IIRFilter is instantiated and then sets
        the coefficients for the filter instance.
        Design of the 'standard' filter types are based upon the equations
        presented by RBJ in the "Cookbook formulae for audio equalizer biquad
        filter coefficients" which can be found at the link below.
        http://shepazu.github.io/Audio-EQ-Cookbook/audio-eq-cookbook.html
        Additional filter designs are also available. Brecht DeMan found that
        the coefficients generated by the RBJ filters do not directly match
        the coefficients provided in the ITU specification. For full compliance
        use the 'DeMan' filters below when constructing filters. Details on his
        work can be found at the GitHub repository below.
        https://github.com/BrechtDeMan/loudness.py
        Returns
        -------
        b : ndarray
            Numerator filter coefficients stored as [b0, b1, b2]
        a : ndarray
            Denominator filter coefficients stored as [a0, a1, a2]
        """
        A  = 10**(self.G/40.0)
        w0 = 2.0 * np.pi * (self.fc / self.rate)
        alpha = np.sin(w0) / (2.0 * self.Q)

        if self.filter_type == 'high_shelf':
            b0 =      A * ( (A+1) + (A-1) * np.cos(w0) + 2 * np.sqrt(A) * alpha )
            b1 = -2 * A * ( (A-1) + (A+1) * np.cos(w0)                          )
            b2 =      A * ( (A+1) + (A-1) * np.cos(w0) - 2 * np.sqrt(A) * alpha )
            a0 =            (A+1) - (A-1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
            a1 =      2 * ( (A-1) - (A+1) * np.cos(w0)                          )
            a2 =            (A+1) - (A-1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
        elif self.filter_type == 'low_shelf':
            b0 =      A * ( (A+1) - (A-1) * np.cos(w0) + 2 * np.sqrt(A) * alpha )
            b1 =  2 * A * ( (A-1) - (A+1) * np.cos(w0)                          )
            b2 =      A * ( (A+1) - (A-1) * np.cos(w0) - 2 * np.sqrt(A) * alpha )
            a0 =            (A+1) + (A-1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
            a1 =     -2 * ( (A-1) + (A+1) * np.cos(w0)                          )
            a2 =            (A+1) + (A-1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
        elif self.filter_type == 'high_pass':
            b0 =  (1 + np.cos(w0))/2
            b1 = -(1 + np.cos(w0))
            b2 =  (1 + np.cos(w0))/2
            a0 =   1 + alpha
            a1 =  -2 * np.cos(w0)
            a2 =   1 - alpha
        elif self.filter_type == 'low_pass':
            b0 =  (1 - np.cos(w0))/2
            b1 =  (1 - np.cos(w0))
            b2 =  (1 - np.cos(w0))/2
            a0 =   1 + alpha
            a1 =  -2 * np.cos(w0)
            a2 =   1 - alpha
        elif self.filter_type == 'peaking':
            b0 =   1 + alpha * A
            b1 =  -2 * np.cos(w0)
            b2 =   1 - alpha * A
            a0 =   1 + alpha / A
            a1 =  -2 * np.cos(w0)
            a2 =   1 - alpha / A
        elif self.filter_type == 'notch':
            b0 =   1 
            b1 =  -2 * np.cos(w0)
            b2 =   1
            a0 =   1 + alpha
            a1 =  -2 * np.cos(w0)
            a2 =   1 - alpha
        elif self.filter_type == 'high_shelf_DeMan':
            K  = np.tan(np.pi * self.fc / self.rate) 
            Vh = np.power(10.0, self.G / 20.0)
            Vb = np.power(Vh, 0.499666774155)
            a0_ = 1.0 + K / self.Q + K * K
            b0 = (Vh + Vb * K / self.Q + K * K) / a0_
            b1 =  2.0 * (K * K -  Vh) / a0_
            b2 = (Vh - Vb * K / self.Q + K * K) / a0_
            a0 =  1.0
            a1 =  2.0 * (K * K - 1.0) / a0_
            a2 = (1.0 - K / self.Q + K * K) / a0_
        elif self.filter_type == 'high_pass_DeMan':
            K  = np.tan(np.pi * self.fc / self.rate)
            a0 =  1.0
            a1 =  2.0 * (K * K - 1.0) / (1.0 + K / self.Q + K * K)
            a2 = (1.0 - K / self.Q + K * K) / (1.0 + K / self.Q + K * K)
            b0 =  1.0
            b1 = -2.0
            b2 =  1.0
        else:
            raise ValueError("Invalid filter type", self.filter_type)            

        self.b, self.a = np.array([b0, b1, b2])/a0, np.array([a0, a1, a2])/a0

    def apply_filter(self, data):
        """ Apply the IIR filter to an input signal.
        Params
        -------
        data : ndarrary
            Input audio data. (samples, channels)
        Returns
        -------
        filtered_signal : ndarray
            Filtered input audio.
        """
        # apply the filter and update the filter state
        y, self.zi = scipy.signal.lfilter(self.b, self.a, data, axis=0, zi=self.zi)

        return self.passband_gain * y

    @property
    def G(self):
        return self.__G
    
    @G.setter
    def G(self, G):
        self.__G = G
        self.generate_coefficients()

    @property
    def Q(self):
        return self.__Q
    
    @Q.setter
    def Q(self, Q):
        self.__Q = Q
        self.generate_coefficients()

    @property
    def fc(self):
        return self.__fc
    
    @fc.setter
    def fc(self, fc):
        self.__fc = fc
        self.generate_coefficients()

    @property
    def rate(self):
        return self.__rate

    @rate.setter
    def rate(self, rate):
        self.__rate = rate
        self.generate_coefficients()

    @property
    def filter_type(self):
        return self.__filter_type

    @filter_type.setter
    def filter_type(self, filter_type):
        self.__filter_type = filter_type
        self.generate_coefficients()

    @property
    def n_channels(self):
        return self.__n_channels

    @n_channels.setter
    def n_channels(self, n_channels):
        self.__n_channels = n_channels
        self.reset_state()