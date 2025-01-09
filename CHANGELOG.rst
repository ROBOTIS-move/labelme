^^^^^^^^^^^^^^^^^^^^^
Changelog for labelme
^^^^^^^^^^^^^^^^^^^^^

5.29.0 (2025-01-09)
-------------------

5.28.0 (2024-12-12)
-------------------

5.27.0 (2024-11-21)
-------------------

5.26.0 (2024-10-11)
-------------------

5.25.0 (2024-09-20)
-------------------

5.24.0 (2024-08-29)
-------------------
* Fixed a bug in setting rectangle and polygon which were set inversely
* Contributors: Dongyun Kim

5.23.0 (2024-08-08)
-------------------
* Added a version checker and enhanced the logging mode for labeling both polygons and bounding boxes
* Contributors: Dongyun Kim

5.22.0 (2024-07-18)
-------------------

5.21.0 (2024-06-27)
-------------------

5.20.0 (2024-06-05)
-------------------

5.19.0 (2024-05-17)
-------------------

5.18.0 (2024-04-18)
-------------------

5.17.0 (2024-03-28)
-------------------
* Added editing bounding box size with top right and bottom left corner and fixed bug in measuring working time
* Contributors: Jongsub Yu

5.16.0 (2024-03-07)
-------------------
* Added functionality to track worker task time and new indoor classes
* Contributors: Dongyun Kim

5.15.0 (2024-02-15)
-------------------
* Changed vehicle color
* Contributors: Jaehun Park

5.14.0 (2024-01-26)
-------------------
* Changed outdoor segmentation label
* Contributors: Jaehun Park

5.13.0 (2023-12-21)
-------------------

5.12.0 (2023-11-30)
-------------------
* Fixed bug of moving box coordinates and modified erasing class list
* Contributors: Jongsub Yu

5.11.0 (2023-11-09)
-------------------
* Added new segmentation class : tree, poll, mat
* Contributors: Jaehun Park

5.10.0 (2023-10-12)
-------------------

5.9.0 (2023-09-21)
------------------
* Added docking-station segmentation class
* Contributors: Jaehun Park

5.8.0 (2023-08-10)
------------------

5.7.0 (2023-07-20)
------------------
* Added segmentation non-target class info
* Contributors: Jaehun Park

5.6.0 (2023-06-29)
------------------

5.5.0 (2023-06-08)
------------------
* Added setting service area as default if the target area does not exist in config file
* Contributors: Jongsub Yu

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
