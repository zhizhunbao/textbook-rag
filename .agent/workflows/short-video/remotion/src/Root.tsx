import React from 'react';
import { Composition, staticFile } from 'remotion';
import { ShortVideo } from './ShortVideo';
import { theme } from './theme';
import type { VideoProps } from './types';

/* 测试数据 — Studio 预览用 */
import testData from '../public/data.json';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* @ts-expect-error — Remotion 4.x Composition generic strict typing */}
      <Composition<VideoProps>
        id="ShortVideo"
        component={ShortVideo}
        width={theme.width}
        height={theme.totalHeight}
        fps={30}
        calculateMetadata={async ({ props }) => {
          if (props.timestamps && props.timestamps.length > 0) {
            const lastTs = props.timestamps[props.timestamps.length - 1];
            const durationInFrames = Math.ceil((lastTs.end + 1) * 30);
            return { durationInFrames };
          }
          return { durationInFrames: 300 };
        }}
        defaultProps={{
          slides: testData.slides,
          timestamps: testData.timestamps,
          audioUrl: staticFile('audio.wav'),
        } as VideoProps}
      />
    </>
  );
};
