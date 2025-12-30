#!/bin/bash

# Function to check if a command exists
command_exists () {
  type "$1" &> /dev/null ;
}

echo "Checking for Doxygen..."
if command_exists doxygen;
then
  echo "Doxygen is installed."
else
  echo "Doxygen is not installed. Please install Doxygen to generate documentation."
  exit 1
fi

echo "Checking for Graphviz (dot command)..."
if command_exists dot;
then
  echo "Graphviz is installed."
else
  echo "Graphviz is not installed. Doxygen will not be able to generate diagrams. Please install Graphviz."
  exit 1
fi

echo "Running Doxygen..."
cd .. # Navigate to the parent directory where Doxyfile is located
doxygen Doxyfile

if [ $? -eq 0 ]; then
  echo "Doxygen documentation generated successfully."
else
  echo "Doxygen encountered an error during documentation generation."
  exit 1
fi
