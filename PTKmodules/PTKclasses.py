"""
Classes and functions used by PracticeTrack.py, a Python ReaScript application
for (Reaper 5.1)

Author: Michael Ellis
Copyright 2015 Ellis & Grant, Inc.
License: Open Source (MIT License)
"""
from reaper_python import *
from PTKutils import dbg, userInputs
import time


def run():
    """
    The toplevel function for this script. Performs the following actions:
    1.  Gather info about the selected media items and tempo/time markers in
        the project.
    2.  Disable UI updates while operating.
    3.  Remove existing tempo/time markers.
    4.  Unselect media items (so we can select each one sequentially).
    5.  Start at the beginning time of the leftmost selected item.
    6.  Replicate each item with ndups copies after it.
    7.  Enable UI updates and update the Arrange window.

    NOTE: This script will not work correctly unless the timebase is set to
    "time" for  items AND tempo time sig markers.  See the File: Project Settings
    dialog to control these items.
    """
    uin = userInputs("Parameters", ndups=1, nbetween=1)
    if uin is None:
        dbg("Cancelled")
        return
    elif uin is False:
        # Bad input
        return
    elif uin.ndups < 0:
        dbg("Can't have negative number of duplicates!")
        return
    elif uin.nbetween < 0:
        dbg("Can't have negative number of bars between items!")
        return
    else:
        ndups = uin.ndups
        nbetween = uin.nbetween

    '''
    Initialize a run timer so we can see how long various parts
    of the processing require.
    '''
    tmr = RunTimer().message
    tmr("Starting run ...")


    '''
    Gather a list of Tempo Time Signature markers in the project
    and create wrappers for them.
    '''
    nsig = RPR_CountTempoTimeSigMarkers(0)
    dbg("{} time signatures in project".format(nsig))
    sigids = range(nsig)
    proj = 0  ## current project

    siglist = []
    for sigid in sigids:
        sig = TempoTimeSigMarkerWrapper(proj, sigid)
        siglist.append(sig)
    tmr("Finished getting siglist")

    '''
    Make a list of selected media items.  We begin with a count of
    the number of selected items.
    '''
    nitems = RPR_CountSelectedMediaItems(0)
    dbg("{} media items selected".format(nitems))
    itemids = range(nitems)
    '''
    Note: the above approach works because the Reaper function
    GetSelectedMediaItem() takes a zero-based index into the set of currently
    selected items as one of its argumemts.  
    See MediaItemRreplicator.__init__() to see how this is used.
    '''

    '''
    Create a list of the selected media items wrapped in MediaItemReplicator instances.
    See below in this file for the class definition.
    '''
    items = []
    for itemid in itemids:
        item = MediaItemReplicator(proj, itemid, siglist)
        #item.dump()
        items.append(item)
    
    '''
    Make a list of the Reaper MediaItem references for each item in
    the user's selections.  
    '''
    selectediids = [item.iid for item in items]

    '''
    We now have a list of current MediaItemReplicator instances for each
    selected media item.  We don't currently handle multiple tracks, so check
    and continue only if all items are in the same track.
    '''

    tracks = [ RPR_GetMediaItem_Track(i.iid) for i in items ]
    dbg(tracks)
    if len(set(tracks)) != 1:
        dbg("Usage Error: All selected items must be in the same track.")
        return
    else:
        track = tracks[0] 

    tmr("Finished setting up selected media item list.")    

    '''
    Now create a list of MediaItemReplicators for ALL items in the track. We'll
    use this to make decisions about how to handle items in the track that are
    not selected.  The ones to the left of the first selection will be left unchanged
    and any that occur after the first selection will be shifted right as needed.
    '''
    ntrackitems = RPR_CountTrackMediaItems(track)
    trackitems = []
    for titemid in range(ntrackitems):
        itemref = RPR_GetTrackMediaItem(track, titemid)
        item = MediaItemReplicator(proj, itemref, siglist, id_is_index=False)
        trackitems.append(item)

    tmr("Finished getting list of ALL media items.")

    '''
    We're ready to start moving and replicating items. Begin by freezing the 
    UI. It's not strictly necessary, but gives better performance.
    '''
    RPR_PreventUIRefresh(1)

    '''
    Delete the existing tempo time sig markers.  We're going to recreate them
    as we go in new locations.
    '''
    for sig in reversed(siglist):
        sig.remove()
    tmr("Finished removing tempo markers.")

    '''
    Unselect all the media items. Our replicator method uses RPR_ApplyNudge()
    which operates on selected items.  We want to have only one item selected
    at a time.
    '''
    RPR_SelectAllMediaItems(0, False)

    '''
    The variable endt represents the ending time position of the item just
    processed. It may or may not include some outtime to finish on a measure
    end.  The important thing is that it represents the earliest time allowed
    for the start of the next item to be processed.
    '''
    endt = 0.0

    '''
    Init a dictionary of tempo time sigs with time position as keys.
    '''
    incountsigd = {}
    for item in trackitems:
        item.dump()
        if item.iid in selectediids:
            endt, _incountsigd = item.replicate(endt, 
                                   ndups, 
                                   nbetween=nbetween)
        else:
            endt, _incountsigd = item.replicate(endt, 
                                   0, 
                                   nbetween = nbetween)

        incountsigd.update(_incountsigd)

    tmr("Finished item processing")

    '''
    Create the incount signatures. These are tempo time signature markers
    that start the count-in before each item. These could have been created
    during the processing, but are deferred until now.  Deferral seemed necessary
    at one point during development, but that turned out not to be the cause of
    the problem I was trying to fix.  Eventually, it may be worthwhile to 
    move the creation back into the replicate() method.
    '''
    sigtimes = getNonRedundantSigTimes(incountsigd)
    tmr("Finished getting non-redundant sig times.")

    for t in sigtimes:
        incountsigd[t].create()

    tmr("Finished creating incount sigs.")

    # clean up the sigs
    #removeRedundantSigs()

    #tmr("Finished removing redundant sigs.")

    # Unfreeze the UI
    RPR_PreventUIRefresh(-1)
    RPR_UpdateArrange()

    tmr("Run completed.")


class TempoTimeSigMarkerWrapper(object):
    """
    Constructed using the list returned from RPR_GetTempoTimeSigMarker().
    Provides create(), set(), dump(), clone(), and remove() methods.

    Initialization ehavior depends on the value you supply for ptidx, the 
    item id.  
    
    For non-negative ptidx, __init__ searches for an existing media
    item with that id.

    Negative ptidx creates a new marker immediately.

    You can defer creation by specifying ptidx=None. The Python object will
    be instantiated immediatly, but the corresponding marker in Reaper will
    not exist until you invoke the the create() method. 


    """
    def __init__(self, proj, ptidx, timepos=0.0, bpm=0.0, num=0, denom=0):
        self.deferred = False
        self.retval = None
        self.proj = proj
        self.timepos = timepos
        self.measurepos = -1
        self.beatpos = -1
        self.bpm = bpm
        self.timesig_num = num
        self.timesig_denom = denom
        self.lineartempo = False

        if ptidx == None:
            self.deferred = True  # Create later
            self.ptidx = -1
        elif ptidx >= 0:
            self.initByIdSearch(proj, ptidx)
        else:
            self.create()
            self.deferred = False

    def create(self):
        """  Create a new marker with specified timepos and bpm """
        ok = RPR_SetTempoTimeSigMarker(self.proj, -1, self.timepos,
                self.measurepos,
                self.beatpos,
                self.bpm,
                self.timesig_num,
                self.timesig_denom,
                self.lineartempo,
                )
        if not ok:
            raise ValueError("Couldn't create tempo time sig marker")
        else:
            dbg("Created marker ({}/{} {}) at timepos {}".format(self.timesig_num,
                                                                 self.timesig_denom,
                                                                 self.bpm,
                                                                 self.timepos))

    def initByIdSearch(self, proj, ptidx):
        """ Init output variables required for call """
        timeposOut = 0.0
        measureposOut = 0
        beatposOut = 0.0
        bpmOut = 0.0
        timesig_numOut = 0
        timesig_denomOut = 0
        lineartempoOut = False

        retlist = RPR_GetTempoTimeSigMarker(proj, ptidx, timeposOut,
                  measureposOut, beatposOut, bpmOut, timesig_numOut,
                  timesig_denomOut, lineartempoOut)

        self.retval = bool(retlist[0])
        self.proj = retlist[1]
        self.ptidx = retlist[2]
        self.timepos = retlist[3]
        self.measurepos = retlist[4]
        self.beatpos = retlist[5]
        self.bpm = retlist[6]
        self.timesig_num = retlist[7]
        self.timesig_denom = retlist[8]
        self.lineartempo = bool(retlist[9])

    def dump(self):
        """ Print neatly to console """
        dbg("retval = {}".format(self.retval))
        dbg("proj = {}".format(self.proj))
        dbg("ptidx = {}".format(self.ptidx))
        dbg("timepos = {}".format(self.timepos))
        dbg("measurepos = {}".format(self.measurepos))
        dbg("beatpos = {}".format(self.beatpos))
        dbg("bpm = {}".format(self.bpm))
        dbg("timesig_num = {}".format(self.timesig_num))
        dbg("timesig_denom = {}".format(self.timesig_denom))
        dbg("lineartempo = {}".format(self.lineartempo))

    def set(self, use_timepos=True):
        """
        Change existing sig with (possibly) altered parameters.
        """
        if use_timepos == True:
            timepos = self.timepos
            measurepos = beatpos = -1
        else:
            measurepos = self.measurepos
            beatpos = self.beatpos
            timepos = -1

        self.retval = RPR_SetTempoTimeSigMarker(self.proj, self.ptidx, timepos,
                                  measurepos, beatpos, self.bpm,
                                  self.timesig_num, self.timesig_denom,
                                  self.lineartempo)

    def clone(self, time_value, is_offset=True, deferred=False):
        """
        Make a copy of this object.
        args:
            - time_value is in seconds. It's interpretation depends on

            - is_offset.  When is_offset is True time_value is added to this
            object's time position, otherwise it is assigned.

            - deferred controls whether the clone is instantiated in Reaper. Deferring
            instantiation in Reaper allows for some performance improvements.
        returns:
            - the cloned instance.
        
        """
        cloned = TempoTimeSigMarkerWrapper(self.proj, self.ptidx)
        if is_offset:
            cloned.timepos = self.timepos + time_value
            dbg("Cloning sig {} with offset {} to {}".format(self.ptidx,
                                                      time_value, 
                                                      cloned.timepos))
        else:
            dbg("Cloning sig {} without offset at {}".format(self.ptidx, time_value))
            cloned.timepos = time_value

        cloned.timesig_num = self.timesig_num
        cloned.timesig_denom = self.timesig_denom
        cloned.bpm = self.bpm
        cloned.lineartempo = self.lineartempo

        cloned.ptidx = -1
        assert cloned.timepos >= 0.0
        if not deferred:
            cloned.set(use_timepos=True)
        return cloned

    def remove(self):
        """
        Tell reaper to delete this marker. Does not delete this Python object,
        however.
        """
        ret = RPR_DeleteTempoTimeSigMarker(self.proj, self.ptidx)
        if ret:
            dbg("Id {} deleted".format(self.ptidx))
        else:
            dbg("Failed deleting Id {}.".format(self.ptidx))

class MediaItemReplicator(object):
    """
    Constructed with calls to RPR Media Item functions.
    Python: (Float retval, ReaProject proj, Float tpos, Int
    measuresOutOptional, Int cmlOutOptional, Float fullbeatsOutOptional, Int
    cdenomOutOptional) = RPR_TimeMap2_timeToBeats(proj, tpos,
    measuresOutOptional, cmlOutOptional, fullbeatsOutOptional,
    cdenomOutOptional)

    convert a time into beats.
    if measures is non-NULL, measures will be set to the measure count, return
        value will be beats since measure.  if cml is non-NULL, will be set to
        current measure length in beats (i.e. time signature numerator) if
        fullbeats is non-NULL, and measures is non-NULL, fullbeats will get the
        full beat count (same value returned if measures is NULL).  if cdenom
        is non-NULL, will be set to the current time signature denominator.

    """
    def __init__(self, proj, itemid, tempotimesiglist, id_is_index=True):
        """
        Note: id_is_index, when True, indicates whether itemid is a zero-based
        index into the set of currently selected media items. When False,
        itemid is interpreted as a Reaper MediaItem reference.
        """
        self.proj = proj
        self.iid = RPR_GetSelectedMediaItem(proj, itemid) if id_is_index else itemid

        self.pos = RPR_GetMediaItemInfo_Value(self.iid, "D_POSITION")
        self.length = RPR_GetMediaItemInfo_Value(self.iid, "D_LENGTH")
        self.end = self.pos + self.length
        '''
        Get beat information at the start of the item.  We need to know how
        far into the current measure the item starts, the measure time signature
        and tempo.
        '''
        measuresOutOptional = 1
        cmlOutOptional = 1
        fullbeatsOutOptional = 1.0
        cdenomOutOptional = 1
        retlist = RPR_TimeMap2_timeToBeats(proj, self.pos, measuresOutOptional,
                  cmlOutOptional, fullbeatsOutOptional, cdenomOutOptional)

        '''
        Beats since the start of the measure where the item begins.
        '''
        self.posbeats = retlist[0]

        '''
        Measure length in beats, i.e., time signature numerator for the
        measure in which the item begins.
        '''
        self.poscml = retlist[4]

        '''
        Time sig denominator at start of item.
        '''
        self.poscdenom = retlist[6]

        '''
        Tempo in bpm taking into account the time sig denominator for the
        measure in which the item begins.
        '''
        self.posbpm = RPR_TimeMap2_GetDividedBpmAtTime(self.proj, self.pos)


        '''
        Gather the same information as above for the measure in which the item
        ends.
        '''
        retlist = RPR_TimeMap2_timeToBeats(proj, self.end, measuresOutOptional,
                  cmlOutOptional, fullbeatsOutOptional, cdenomOutOptional)
        self.endbeats = retlist[0]
        self.endcml = retlist[4]
        self.endcdenom = retlist[6]
        self.endbpm = RPR_TimeMap2_GetDividedBpmAtTime(self.proj, self.end)
        
        '''
        Check to see if the ending is a tiny amount after a barline.  This causes a
        full measure length of the following segment's tempo to be inserted while
        the tempo is still at the prior value.  It creates an obvious timing
        problem if this happens across a significant tempo change.

        To avoid this, we'll remap with the endpoint reduced by .001 seconds.
        '''
        if self.endbeats < .001:
            self.length -= 0.001
            self.end = self.pos + self.length
            retlist = RPR_TimeMap2_timeToBeats(proj, self.end, measuresOutOptional,
                      cmlOutOptional, fullbeatsOutOptional, cdenomOutOptional)
            self.endbeats = retlist[0]
            self.endcml = retlist[4]
            self.endcdenom = retlist[6]
            self.endbpm = RPR_TimeMap2_GetDividedBpmAtTime(self.proj, self.end)   



        '''
        Save a reference to the full list of all time signatures in the
        project.
        '''
        self.tempotimesiglist = tempotimesiglist

        '''
        Compute 2 values used in spacing between items.  Intime is
        the bar time before the item starts.
        Outttime is the time remaining in the bar at the end of the item.
        Unit for intime and outttime is seconds.
        '''
        intimebeats = self.posbeats
        secondsperbeat = 60./self.posbpm
        self.intime = secondsperbeat * intimebeats

        outtimebeats = self.endcml - self.endbeats
        secondsperbeat = 60./self.endbpm
        self.outtime = outtimebeats * secondsperbeat

    def dump(self):
        """ Neatly print attributes """
        dbg("proj = {}".format(self.proj))
        dbg("iid = {}".format(self.iid))
        dbg("pos = {}".format(self.pos))
        dbg("length = {}".format(self.length))
        dbg("posbeats = {}".format(self.posbeats))
        dbg("poscml = {}".format(self.poscml))
        dbg("poscdenom = {}".format(self.poscdenom))
        dbg("posbpm = {}".format(self.posbpm))
        dbg("endbeats = {}".format(self.endbeats))
        dbg("endcml = {}".format(self.endcml))
        dbg("endcdenom = {}".format(self.endcdenom))
        dbg("endbpm = {}".format(self.endbpm))
        dbg("intime = {}".format(self.intime))
        dbg("outtime = {}".format(self.outtime))

    def replicate(self, t0, ndups, nbetween=0):
        """
        Make 0 or more copies of an item and preserve the surrounding meter
        positions and tempi.

        Details of what this method does:

            Move item to t0 and follow it with ndups copies. Include outtime
            after original and all copies.  Prepend nbetween full measures +
            intime to all copies.

            Replicate all tempo time signature marker in original and copies.
            Make sure that the moved original begins with the correct tempo and
            time sig.  Ditto for each copy starting with the incount.

            The resulting sequence for each item looks like: betweentime intime
            orig outtime [ [ betweentime intime dup outtime] ... ]

            Return t0 + sum of all time added such that the returned time
            corresponds to the end of the last outtime.

        """


        '''
        First, find all the tempo time sig markers in the item.item and locate
        the marker for the sig in effect at the beginning of the item. The
        latter will be used for the lead-in count.
        '''

        itemsigs = []
        insig = self.tempotimesiglist[0] # earliest possible
        for sig in self.tempotimesiglist:
            if self.pos <= sig.timepos < (self.pos + self.length):
                dbg("Sig {} is in this item".format(sig.ptidx))
                itemsigs.append(sig)
                #sig.dump()
            if sig.timepos <= self.pos + .001:
                insig = sig
        incountsigd = {}

        #dbg("\nIncount sig info:")
        #incountsig.dump()
        #dbg("")

        # select the item (so we can use ApplyNudge())
        RPR_SetMediaItemSelected(self.iid, True)

        # Caculate destination time position
        t = t0
        dbg("Entering replicate() with t={}".format(t))
        incountsigd[t] = (TempoTimeSigMarkerWrapper(self.proj, None,
                timepos = t,
                bpm = insig.bpm,
                num = insig.timesig_num,
                denom = insig.timesig_denom))


        betweentime = nbetween * self.poscml * 60./self.posbpm
        dbg("betweentime = {}".format(betweentime))
        t += betweentime + self.intime

        # Move the item if need be
        if t > self.pos:
            RPR_SetMediaItemInfo_Value(self.iid, "D_POSITION", t)
            dbg('Item moved to {}'.format(t))

        # copy the tempo time markers to the new location.
        for sig in itemsigs:
            newpos = t
            incountsigd[t] = sig.clone(newpos - self.pos, deferred=True)

        # Advance to end of item
        t += self.length
        t += self.outtime

        # Apppend the requested number of duplicates.
        for _ in range(ndups):
            # Insert a tempo time at start of incount measure.
            incountsigd[t] = (TempoTimeSigMarkerWrapper(self.proj, None,
                timepos = t,
                bpm = insig.bpm,
                num = insig.timesig_num,
                denom = insig.timesig_denom))

            dbg("incount marker position = {}".format(t))

            # Advance to beginning of new item position.
            t += betweentime + self.intime

            # Clone the tempo time sigs
            for sig in itemsigs:
                newpos = t
                incountsigd[t] = sig.clone(newpos - self.pos, deferred=True)

            # Compute the offset for duplication
            nudge = self.length 
            nudge += self.outtime
            nudge += betweentime
            nudge += self.intime

            # Duplicate the item using ApplyNudge and the flags
            # assigned below. See API doc for more info about args
            # to ApplyNudge().
            fbyvalue = 0
            fduplicate = 5
            fseconds = 1
            freverse = False
            RPR_ApplyNudge(self.proj, fbyvalue, fduplicate, fseconds,
                           nudge, freverse, 1)
            
            dbg("Item duped offset by {}".format(nudge))

            # Advance to end of last measure in item
            t += self.length + self.outtime

        dbg("")  # blank line in console log

        # Unselect the item
        RPR_SetMediaItemSelected(self.iid, False)

        # Return end time for last dup so we can use it as
        # the start of the next item to be processed.
        return t, incountsigd

class RunTimer(object):
    """
    Instantiate one of these and use it to display messages with
    elapsed time prepended, e.g.

    tmr = RunTimer().message
    # later
    tmr("In foo() about to call bar().")
    """
    def __init__(self):
        self.start = time.time()
    
    def message(self, obj):
        elapsed = time.time() - self.start
        msg = "{}: {}".format(elapsed, obj)
        dbg(msg)
        return msg

def equivalentSigs(sig1, sig2):
    """
    Return True if both sigs have the same tempo and time signature.
    """
    return (sig1.bpm == sig2.bpm and 
            sig1.timesig_num == sig2.timesig_num and
            sig1.timesig_denom == sig2.timesig_denom and
            sig1.lineartempo == sig2.lineartempo)


def getNonRedundantSigTimes(sigd):
    """
    Return a list of time positions in ascending order that correspond
    to signatures that are not duplicates of their immmediate predecessors.

    args:
        - sigd : a dictionary of TempoTimeSigMarkerWrappers with time
                 positions as keys.

    """
    ## list the keys in reverse order
    sigtimes_r = sorted(sigd.keys(), reverse=True)
    ## Init a list for the non-redundant keys
    nrkeys = []
    ## check each sig for equivalence with its predecessor.
    for i, t in enumerate(sigtimes_r[0:-1]):
        current = sigd[sigtimes_r[i]]
        previous = sigd[sigtimes_r[i+1]]
        if not equivalentSigs(previous, current):
            dbg("Sig at {} is non-redundant".format(t))
            nrkeys.insert(0,t)
    return nrkeys        


def removeRedundantSigs():
    """
    Remove all tempo time sigs that are duplicates of  the sig immediately
    preceding.
    """
     ## TempoTimeSigMarkers
    nsig = RPR_CountTempoTimeSigMarkers(0)
    dbg("Entering removeRedundantSigs()")
    dbg("{} time signatures in project".format(nsig))
    sigids = range(nsig)
    proj = 0  ## current project

    siglist = []
    for sigid in sigids:
        sig = TempoTimeSigMarkerWrapper(proj, sigid)
        siglist.append(sig)

    ilast = len(siglist) - 1
    while ilast > 0:
        dbg("Checking sig {}".format(ilast))
        if equivalentSigs(siglist[ilast], siglist[ilast - 1]):
            dbg("Removing sig {}".format(ilast))
            siglist[ilast].remove()
        ilast -= 1

        

