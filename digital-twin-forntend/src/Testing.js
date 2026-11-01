import React from 'react';
import ReactPlayer from 'react-player';
const Testing = () => {
    return (
        <ReactPlayer
          url="https://static.videezy.com/system/resources/previews/000/041/016/original/alb_tvn0411_1080p.mp4"
          playing
          muted
          controls
          width="100%"
          height="100%"
          config={{
            file: {
              attributes: {
                autoPlay: true,
                muted: true,
                playsInline: true,
                controlsList: 'nodownload',
              },
            },
          }}
          //onReady={() => console.log('Player is ready')}
          onError={(e) => console.error('Playback error:', e)}
        />
      );
  };
  
  export default Testing;
  