# Practice-Track
A Reaper ReaScript for creating rehearsal tracks from audio files.

From a contiguous group of selected media items, ABC..., creates a practice track
such that ABC ...  ==>  A A B B C C ...  where the spaces between the letters
indicate one bar of silence in the tempo and meter at the beginning of the
original item.  Properly replicates all tempo and meter changes within items to
facilitate practicing in correct rhythm.

![Animation](practicetrack.gif)

> Author: Michael Ellis

> Copyright 2015 Ellis & Grant, Inc.

> License: Open Source (MIT License)

> No warranty whatsoever ... etc.

Installation:
    This file and the subdirectory PTKmodules need to be in a directory where
    Reaper expects to find scripts. See the Reaper User Guide for details on
    paths.  You can also put these files in any convenient directory and simply
    load this script from the Actions List dialog. Reaper will remember it
    thereafter.

    (You also need to enable Python scripting in Reaper and have a working
    Python installation.)

Typical Usage:

    1. In Reaper, slice an audio track into contiguous media items representing
       short segments to be rehearsed.  For best results, the track should be
       tempo mapped so that the grid corresponds accurately to each measure of
       music. The SWS extensions provide some nice ways to do this efficiently.
       See [Tempo Mapping](http://wiki.cockos.com/wiki/index.php/Tempo_mapping_with_SWS) for
       details.

    2. IMPORTANT! Make sure the timebase is set to 'time' for both items and markers.

    3. Select all the items in the track. (You can also select a contiguous
       group of items extending to the end of the track. This would leave items to
       the left of the first selected item unchanged.)

    4. Invoke PracticeTrack.py (this file) from the Actions menu.

    5. A 'Parameters' dialog appears. 
            Fill in an integer value for the number of duplicates to be created
            for each item. The default is '1', any value >= 0 is acceptable.

            Fill in an integer values for the number of bars of silence to insert
            between items. The default is '1', any value >= 0 is acceptable.   

    6. Click OK. Processing is quote fast, much less than 1 second for typical projects.
       Should something go wrong, 'Edit Undo' will revert your project in one step.

    7. Edit the project as needed to create your practice track.

    8. Happy rehearsing!                                
