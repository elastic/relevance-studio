/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import {
  EuiInputPopover,
  EuiSelectable,
} from '@elastic/eui'

const SelectScenario = ({
  autoFocus = false,
  isLoading,
  isOpen,
  onChange,
  options,
  placeholder = 'Choose a scenario',
  searchString,
  setSearchString,
  setIsLoading,
  setIsOpen,
  setOptions,
}) => {
  return (
    <EuiSelectable
      emptyMessage={
        isLoading || options.length === 0 && !searchString
          ? 'Loading scenarios...'
          : 'No scenarios found'
      }
      isPreFiltered
      listProps={{
        css: { '.euiSelectableList__list': { maxBlockSize: 200 } },
      }}
      options={options}
      onChange={(newOptions, event, changedOption) => {
        setOptions(newOptions)
        setIsOpen(false)
        setIsLoading(false)
        if (onChange) {
          onChange(changedOption)
        }
      }}
      singleSelection
      searchable
      searchProps={{
        autoFocus: autoFocus,
        isClearable: false,
        isLoading: isLoading,
        onChange: (value) => {
          setSearchString(value)
        },
        onKeyDown: (event) => {
          if (event.key === 'Tab') return setIsOpen(false)
          if (event.key !== 'Escape') return setIsOpen(true)
        },
        onClick: () => {
          // Clear search string when opening dropdown to show all scenarios
          if (!isOpen) {
            setSearchString('')
          }
          setIsOpen(true)
        },
        onFocus: () => {
          // Clear search string when opening dropdown to show all scenarios
          if (!isOpen) {
            setSearchString('')
          }
          setIsOpen(true)
        },
        placeholder: isLoading ? '' : placeholder,
        value: searchString,
      }}
    >
      {(options, searchString) => (
        <EuiInputPopover
          closeOnScroll
          closePopover={() => setIsOpen(false)}
          disableFocusTrap
          fullWidth
          input={searchString}
          isOpen={isOpen}
          panelPaddingSize='none'
        >
          {options}
        </EuiInputPopover>
      )}
    </EuiSelectable>
  )
}

export default SelectScenario