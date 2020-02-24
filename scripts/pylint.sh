# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

set -ev

# Run pylint on directories
function pylint_dir {
  python -m pip install --upgrade pylint
  pylint $(find azure_monitor -type f -name "*.py")
  return $?
}

pylint_dir
