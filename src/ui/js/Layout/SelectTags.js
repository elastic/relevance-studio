/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

import { useState } from 'react'
import {
  EuiFilterButton,
  EuiFilterGroup,
  EuiPopover,
  EuiSelectable,
} from '@elastic/eui'

// A multi-select "Tags" filter button + popover checklist. Selecting or
// deselecting a tag calls `onChange` with the full next list of selected
// tags; callers are responsible for turning that into a server-side filter
// (e.g. a `terms` query) and re-fetching.
const SelectTags = ({ isLoading, options = [], selected = [], onChange }) => {

  ////  State  /////////////////////////////////////////////////////////////////

  const [isOpen, setIsOpen] = useState(false)

  ////  Render  ////////////////////////////////////////////////////////////////

  const selectableOptions = options.map((tag) => ({
    label: tag,
    checked: selected.includes(tag) ? 'on' : undefined,
  }))

  return (
    <EuiFilterGroup>
      <EuiPopover
        button={
          <EuiFilterButton
            iconType='arrowDown'
            isSelected={isOpen}
            onClick={() => setIsOpen(!isOpen)}
            hasActiveFilters={selected.length > 0}
            numActiveFilters={selected.length || undefined}
            numFilters={options.length}
            isLoading={isLoading}
          >
            Tags
          </EuiFilterButton>
        }
        closePopover={() => setIsOpen(false)}
        isOpen={isOpen}
        panelPaddingSize='none'
      >
        <EuiSelectable
          emptyMessage={isLoading ? 'Loading tags...' : 'No tags found'}
          isLoading={isLoading}
          listProps={{
            css: { '.euiSelectableList__list': { maxBlockSize: 200 } },
          }}
          onChange={(newOptions) => {
            onChange(newOptions.filter((o) => o.checked === 'on').map((o) => o.label))
          }}
          options={selectableOptions}
          searchable
        >
          {(list, search) => (
            <div style={{ width: 300 }}>
              {search}
              {list}
            </div>
          )}
        </EuiSelectable>
      </EuiPopover>
    </EuiFilterGroup>
  )
}

export default SelectTags
