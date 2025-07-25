import { useRef, useState } from 'react'
import {
  euiPaletteForStatus,
  EuiButtonIcon,
  EuiFlexGroup,
  EuiFlexItem,
  EuiForm,
  EuiLoadingSpinner,
  EuiPanel,
  EuiRange,
  EuiText,
  EuiToolTip,
} from '@elastic/eui'
import { useAppContext } from '../Contexts/AppContext'
import { usePageResources } from '../Contexts/ResourceContext'
import { DocCard } from '../Layout'
import api from '../api'
import utils from '../utils'

const JudgementCard = ({ _id, doc, scenario, template, ...props }) => {

  ////  Context  ///////////////////////////////////////////////////////////////

  const { addToast } = useAppContext()
  const { project } = usePageResources()

  ////  State  /////////////////////////////////////////////////////////////////

  const [judgementId, setJudgementId] = useState(props._id)
  const [loadingRating, setLoadingRating] = useState(false)
  const [createdBy, setCreatedBy] = useState(props.createdBy)
  const [updatedBy, setUpdatedBy] = useState(props.updatedBy)
  const [rating, setRating] = useState(props.rating)
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
      const newDoc = {
        index: doc._index,
        doc_id: doc._id,
        rating: parseInt(rating),
      }
      let response
      try {
        setLoadingRating(true)
        response = await api.judgements_set(project._id, scenario._id, newDoc)
      } catch (e) {
        setRating(lastCommittedRating.current)
        return addToast(api.errorToast(e, { title: 'Failed to set rating' }))
      } finally {
        setLoadingRating(false)
        dragging.current = false
      }
      if (response.status > 299) {
        setRating(lastCommittedRating.current)
        addToast(utils.toastClientResponse(response))
      } else {
        lastCommittedRating.current = rating
        setCreatedBy('unknown')
        setUpdatedBy('unknown')
        setJudgementId(response.data._id)
      }
    })()
  }

  const onClearRating = () => {
    (async () => {
      let response
      try {
        setLoadingRating(true)
        response = await api.judgements_unset(project._id, judgementId)
      } catch (e) {
        setRating(lastCommittedRating.current)
        return addToast(api.errorToast(e, { title: 'Failed to unset rating' }))
      } finally {
        setLoadingRating(false)
        dragging.current = false
      }
      if (response.status > 299) {
        setRating(lastCommittedRating.current)
        addToast(utils.toastClientResponse(response))
      } else {
        setRating(null)
        lastCommittedRating.current = null
        setCreatedBy(null)
        setUpdatedBy(null)
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

  return (
    <EuiPanel paddingSize='none'>
      <EuiForm>
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
              <EuiFlexItem grow style={{ overflow: 'hidden' }}>
                <EuiPanel
                  className='judgement-card-range-slider'
                  hasBorder
                  paddingSize='none'
                  style={{
                    borderTopLeftRadius: 0,
                    borderTopRightRadius: 0,
                    marginTop: '-1px',
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
                      levels={rating >= 0 ? [
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
                  {(createdBy || updatedBy) &&
                    <EuiToolTip
                      content={`Rated by ${createdBy == 'ai' ? 'AI' : 'human'}`}
                      anchorProps={{
                        style: {
                          marginLeft: '19px'
                        }
                      }}
                    >
                      <EuiButtonIcon
                        aria-label={`Rated by ${updatedBy || createdBy}`}
                        color={(updatedBy || createdBy) == 'ai' ? 'primary' : 'text'}
                        display={(updatedBy || createdBy) == 'ai' ? 'base' : 'empty'}
                        iconSize='m'
                        iconType={(updatedBy || createdBy) == 'ai' ? 'sparkles' : 'user'}
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
            hasShadow: false,
            style: {
              borderTopLeftRadius: 0,
              borderTopRightRadius: 0
            }
          }}
          body={template?.body}
          imagePosition={template?.image?.position}
          imageUrl={template?.image?.url}
          showScore={props.showScore}
        />
      </EuiForm>
    </EuiPanel>
  )
}

export default JudgementCard