BookAssemblyController ---> Will Remain in Java or needs to call Java Process
EndpointDocController --> Does Not appear to be used.
PhotoController  --> PhotoRepo
PhotoGalleryController  --> PhotoRepo
PhotoRepoController  --> PhotoRepo
PhotoRepoTagController  --> PhotoRepo
RestController Doesn't need to be implemented
SavedSearchController -- Not Sure.
SheetVersionController --> Not being used



BookController  Implementing as projects


HeartbeatController --> Needs to be implemented
LoginController --> Needs to be implemented

UserController --> Needs to be implemented
MockKeystoneController -> Handled through the enfold client


Initially Implemented In Mongo Needs to Be Migrated:

* ClipArtImageController
* FontController
* TemplateController
* ThemeController --> POST Method Not Implemented...Doesn't look to be used anywhere.
* BookConfigController Only GET on collection implement...everything else isnt used.
* BackgroundImageController... Only Implemeted collection GET...everything else is not used.

Implemented In Python + SQL:

* ProjectController Being Implemented as Projects
* SheetController --> Being implemented as Sheets resource