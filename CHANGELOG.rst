^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changelog for package labelme
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

5.4.0 (2023-05-18)
------------------

5.3.0 (2023-04-27)
------------------
* Added setting specific labels according to service area
* Added new service area with new target classes
* Contributors: Jongsub Yu

5.2.0 (2023-04-06)
------------------

5.1.0 (2023-03-16)
------------------

5.0.0 (2023-02-23)
------------------

4.11.0 (2023-02-02)
-------------------
* Fixed adding point outside of the image bug
* Modified calculating offset of polygon when moving towards the edge of the image
* Contributors: Jongsub Yu

4.10.0 (2023-01-12)
-------------------

4.9.0 (2022-12-22)
------------------
* Deactivated delete file button
* Contributors: Jongsub Yu

4.8.0 (2022-12-01)
------------------

4.7.0 (2022-11-11)
------------------
* Added image pop-up function for review
* Added label converting buttons and pop-up windows
* Added a new segmentation class for midas data labeling
* Added arrow key shortcuts for loading next/previous image
* Added q shortcuts to delete label
* Added delete pop-up option
* Added function to edit label name
* Added function to move box point
* Added function to view label probabilities
* Added function to reset to previous brightness and contrast
* Contributors: Eungi Cho

4.6.0 (2022-10-21)
------------------

4.5.0 (2022-09-30)
------------------
* Added exception handling for key input mistakes during labeling
* Added previous brightness and contrast keeping mode
* Added a new outdoor segmentation class for midas data labeling
* Contributors: Eungi Cho

4.4.0 (2022-08-26)
------------------
* Changed color visualization rules
* Added shortcuts for hide and show all
* Changed the category name of indoor segmentation
* Added color to segmentation converting error message
* Modified draw_segment_label codes for indoor segmentation
* Modified a label dialog popup position
* Fixed a intersection point bug
* Activated brightness and contrast options
* Changed the category name of indoor segmentation
* Contributors: Eungi Cho, Dongyun Kim

4.3.0 (2022-07-15)
------------------
* Added redo function
* Added exception handling of auto save mode
* Added bounding box draw guide lines
* Added display label option of create rectangle mode
* Added category for elevator button segmentation
* Added single class labeling mode
* Added new outdoor detection classes such as animal, unknown, countdown-walk and countdown-light-out
* Modified moving label function in edit mode
* Contributors: Eungi Cho

4.2.0 (2022-06-24)
------------------
* Added multiprocessing of segmentation converter
* Changed class color of cross-walk and braille-block
* Contributors: Eungi Cho

4.1.0 (2022-05-27)
------------------
* Changed matplotlib default version
* Changed default label colors for visualization
* Added mode selection function for add point to edge
* Fixed cursor shape to normal cursor
* Contributors: Eungi Cho

4.0.0 (2022-05-04)
------------------
* Modified labelme for labeling by Robotis Algorithm Team
* Added labeling classes for detection and segmentation
* Added 3d object labeling function
* Added visualization function for static object labeling reference lines
* Added labeling type activation function for labeling according to deep learning task
* Contributors: Eungi Cho
