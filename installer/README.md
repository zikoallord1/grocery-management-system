# Windows Production Installer

The production Windows installer must be generated as a self-contained Setup.exe that installs all runtime dependencies required by the application on a clean Windows machine. The CI workflow intentionally fails when no real Setup.exe is produced; a copied source/build directory is not accepted as a release installer.
