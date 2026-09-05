class BuyingSignalException(Exception): pass
class BuyingSignalNotFoundException(BuyingSignalException): pass
class DuplicateBuyingSignalException(BuyingSignalException): pass
class InvalidCompanyException(BuyingSignalException): pass
class InvalidMissionException(BuyingSignalException): pass
