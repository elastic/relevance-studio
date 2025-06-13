import React, { useRef, useState } from 'react'
import {
  euiPaletteForStatus,
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiIcon,
  EuiLoadingSpinner,
  EuiPanel,
  EuiRange,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import DocCard from '../Displays/DocCard'
import { useAppContext } from '../../Contexts/AppContext'
import { useProjectContext } from '../../Contexts/ProjectContext'
import api from '../../api'
import utils from '../../utils'

const JudgementsCard = ({ doc, scenario, template, ...props }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = useProjectContext()

  ////  State  /////////////////////////////////////////////////////////////////

  const [loadingRating, setLoadingRating] = useState(false)
  const [author, setAuthor] = useState(props.author)
  const [rating, setRating] = useState(props.rating)
  const [timestamp, setTimestamp] = useState(props.timestamp)
  const dragging = useRef(false)
  const lastCommittedRating = useRef(rating)

  const onChangeRating = (newRating) => {
    setRating(newRating)
    dragging.current = true
  }

  const onCommitRating = () => {
    dragging.current = false
    if (rating == lastCommittedRating.current)
      return;
    (async () => {

      // Submit API request
      const newDoc = {
        index: doc._index,
        doc_id: doc._id,
        rating: rating,
      }
      let response
      try {
        setLoadingRating(true)
        response = await api.set_judgement(project._id, scenario._id, newDoc)
      } catch (err) {
        setRating(lastCommittedRating.current)
        return addToast(api.errorToast(err, { title: 'Failed to get scenarios' }))
      } finally {
        setLoadingRating(false)
        dragging.current = false
      }

      // Handle API response
      if (response.status >= 200 && response.status <= 299) {
        lastCommittedRating.current = rating
        setAuthor('human')
      } else {
        setRating(lastCommittedRating.current)
        addToast(utils.toastClientResponse(response))
      }
    })()
  }

  const onClearRating = () => {
    (async () => {

      // Submit API request
      const _doc = {
        index: doc._index,
        doc_id: doc._id
      }
      let response
      try {
        setLoadingRating(true)
        response = await api.unset_judgement(project._id, scenario._id, _doc)
      } catch (err) {
        setRating(lastCommittedRating.current)
        return addToast(api.errorToast(err, { title: 'Failed to get scenarios' }))
      } finally {
        setLoadingRating(false)
        dragging.current = false
      }

      // Handle API response
      if (response.status >= 200 && response.status <= 299) {
        setRating(null)
        lastCommittedRating.current = null
        setAuthor(null)
      } else {
        setRating(lastCommittedRating.current)
        addToast(utils.toastClientResponse(response))
      }
    })()
  }

  ////  Render  ////////////////////////////////////////////////////////////////

  const colorBands = euiPaletteForStatus(project.rating_scale.max - project.rating_scale.min + 1).reverse()

  const ticks = []
  for (var i = project.rating_scale.min; i <= project.rating_scale.max; i++) {
    ticks.push({
      label: <EuiText color='subdued' size='xs'><small>{i}</small></EuiText>,
      value: i
    })
  }

  const description = <EuiForm>
    <EuiFlexGroup alignItems='center' gutterSize='none'>
      <EuiFlexItem grow>
        <EuiFlexGroup gutterSize='none'>
          <EuiFlexItem grow={false} style={{ align: 'center', height: '38px', width: '37px' }}>
            {!!lastCommittedRating.current &&
              <EuiPanel
                hasBorder={false}
                hasShadow={false}
                paddingSize='none'
                style={{
                  borderBottomLeftRadius: 0,
                  borderBottomRightRadius: 0,
                  borderRightStyle: 'none',
                  borderTopRightRadius: 0
                }}>
                {loadingRating &&
                  <EuiLoadingSpinner
                    size='l'
                    style={{
                      position: 'absolute',
                      left: '7px',
                      top: '7px'
                    }}
                  />
                }
                {!loadingRating &&
                  <EuiToolTip
                    content='Clear rating'
                    anchorProps={{
                      style: {
                        marginLeft: '20px'
                      }
                    }}
                  >
                    <EuiButtonIcon
                      aria-label='Clear rating'
                      color='text'
                      disabled={loadingRating}
                      display='empty'
                      iconSize='s'
                      iconType='cross'
                      onClick={onClearRating}
                      size='s'
                      style={{
                        position: 'absolute',
                        left: '3px',
                        top: '3px'
                      }}
                    />
                  </EuiToolTip>
                }
              </EuiPanel>
            }
          </EuiFlexItem>
          <EuiFlexItem grow>
            <EuiPanel
              hasBorder
              paddingSize='none'
              style={{
                borderTopLeftRadius: 0,
                borderTopRightRadius: 0,
              }}
            >
              <div
                onKeyUp={onCommitRating}
                onMouseUp={onCommitRating}
                onTouchEnd={onCommitRating}
                style={{
                  marginTop: '2px'
                }}>
                <EuiRange
                  compressed
                  disabled={loadingRating}
                  fullWidth
                  min={project.rating_scale.min}
                  max={project.rating_scale.max}
                  levels={rating ? [
                    {
                      color: colorBands[rating],
                      min: project.rating_scale.min,
                      max: project.rating_scale.max
                    }
                  ] : [
                    {
                      color: 'text'
                    }
                  ]}
                  onChange={(e) => onChangeRating(e.target.value)}
                  showRange
                  showTicks
                  step={1}
                  ticks={ticks}
                  value={rating || 0}
                />
              </div>
            </EuiPanel>
          </EuiFlexItem>
          <EuiFlexItem grow={false} style={{ align: 'center', height: '38px', width: '37px' }}>
            <EuiPanel
              hasBorder={false}
              hasShadow={false}
              paddingSize='none'
              style={{
                borderBottomLeftRadius: 0,
                borderBottomRightRadius: 0,
                borderRightStyle: 'none',
                borderTopRightRadius: 0
              }}>
              {author &&
                <EuiToolTip
                  content={`Rated by ${author == 'ai' ? 'AI' : 'human'}`}
                  anchorProps={{
                    style: {
                      marginLeft: '19px'
                    }
                  }}
                >
                  <EuiButtonIcon
                    aria-label={`Rated by ${author}`}
                    color={author == 'ai' ? 'primary' : 'text'}
                    display={author == 'ai' ? 'base' : 'empty'}
                    iconSize='m'
                    iconType={author == 'ai' ? 'sparkles' : 'user'}
                    onClick={() => { }}
                    size='s'
                    style={{
                      position: 'absolute',
                      right: '3px',
                      top: '3px'
                    }}
                  />
                </EuiToolTip>
              }
            </EuiPanel>
          </EuiFlexItem>
        </EuiFlexGroup>
      </EuiFlexItem>
    </EuiFlexGroup>
    <DocCard
      doc={doc}
      panelProps={{
        hasBorder: false,
        style: {
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0
        }
      }}
      body={template?.body}
      imagePosition={template?.image?.position}
      imageUrl={template?.image?.url}
    />
  </EuiForm>

  return (
    <EuiPanel hasBorder paddingSize='none'>
      {description}
    </EuiPanel>
  )
}

export default JudgementsCard