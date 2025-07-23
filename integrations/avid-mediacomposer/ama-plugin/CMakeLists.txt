cmake_minimum_required(VERSION 3.16)
project(MAMS_AMA_Plugin VERSION 1.0.0)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Avid AMA SDK
find_path(AVID_AMA_SDK_DIR
    NAMES include/AMA/IMANode.h
    PATHS
        "$ENV{AVID_AMA_SDK}"
        "/opt/Avid/AMA_SDK"
        "C:/Program Files/Avid/AMA_SDK"
    DOC "Avid AMA SDK directory"
)

if(NOT AVID_AMA_SDK_DIR)
    message(FATAL_ERROR "Avid AMA SDK not found. Please set AVID_AMA_SDK environment variable.")
endif()

# Include directories
include_directories(
    ${AVID_AMA_SDK_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
)

# Source files
set(SOURCES
    src/MAMSPlugin.cpp
    src/MAMSContainer.cpp
    src/MAMSClip.cpp
    src/MAMSEssence.cpp
    src/MAMSMetadata.cpp
    src/MAMSAPIClient.cpp
    src/MAMSCache.cpp
    src/MAMSUtils.cpp
)

set(HEADERS
    src/MAMSPlugin.h
    src/MAMSContainer.h
    src/MAMSClip.h
    src/MAMSEssence.h
    src/MAMSMetadata.h
    src/MAMSAPIClient.h
    src/MAMSCache.h
    src/MAMSUtils.h
)

# Platform-specific settings
if(WIN32)
    set(SOURCES ${SOURCES} src/MAMSPlugin.def)
    add_definitions(-DWIN32 -D_WINDOWS -D_USRDLL)
    set(CMAKE_SHARED_LIBRARY_PREFIX "")
    set(CMAKE_SHARED_LIBRARY_SUFFIX ".dll")
elseif(APPLE)
    set(CMAKE_MACOSX_RPATH ON)
    set(CMAKE_SHARED_LIBRARY_SUFFIX ".bundle")
    set(CMAKE_SHARED_MODULE_SUFFIX ".bundle")
endif()

# Create shared library
add_library(MAMS_AMA SHARED ${SOURCES} ${HEADERS})

# Link libraries
if(WIN32)
    target_link_libraries(MAMS_AMA
        ${AVID_AMA_SDK_DIR}/lib/AMACore.lib
        ws2_32
        winhttp
    )
elseif(APPLE)
    target_link_libraries(MAMS_AMA
        ${AVID_AMA_SDK_DIR}/lib/libAMACore.dylib
        "-framework CoreFoundation"
        "-framework Security"
        curl
    )
endif()

# Set output directory
set_target_properties(MAMS_AMA PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/bin"
)

# Install rules
if(WIN32)
    install(TARGETS MAMS_AMA
        RUNTIME DESTINATION "C:/Program Files/Avid/AMA_Plug-ins/MAMS"
    )
elseif(APPLE)
    install(TARGETS MAMS_AMA
        LIBRARY DESTINATION "/Library/Application Support/Avid/AMA/Plug-ins"
    )
endif()

# Create plugin info file
configure_file(
    ${CMAKE_CURRENT_SOURCE_DIR}/PluginInfo.xml.in
    ${CMAKE_BINARY_DIR}/bin/PluginInfo.xml
    @ONLY
)