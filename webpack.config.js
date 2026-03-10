/*
 * Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
 * or more contributor license agreements. Licensed under the Elastic License
 * 2.0; you may not use this file except in compliance with the Elastic License
 * 2.0.
 */

const path = require('path')
const CopyWebpackPlugin = require('copy-webpack-plugin')
const HtmlWebpackPlugin = require('html-webpack-plugin')

module.exports = {
  entry: ['./src/ui/js/index.js'],
  output: {
    filename: 'main.js',
    path: path.resolve(__dirname, 'dist'),
    publicPath: '/'
  },
  module: {
    rules: [
      {
        test: /\.(js|tsx?)$/,
        use: 'babel-loader',
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: [
          {
              loader: 'style-loader'
          },
          {
              loader: 'css-loader'
          }
        ]
      },
      {
        test: /\.(woff|woff2|ttf|eot|ico|png|gif|jpg|jpeg)(\?|$)/,
        use: 'file-loader'
      },
      {
        test: /\.html$/,
        use: 'html-loader'
      }
    ]
  },
  plugins: [
    new HtmlWebpackPlugin({
        template: './src/ui/index.html'
    }),
    new CopyWebpackPlugin({
      patterns: [
        {
          from: path.resolve(__dirname, 'src/ui/img'),
          to: path.resolve(__dirname, 'dist/img')
        },
        {
          from: path.resolve(__dirname, 'node_modules/monaco-editor/min'),
          to: path.resolve(__dirname, 'dist/monaco-editor/min')
        }
      ]
    })
  ],
  resolve: {
    extensions: ['.js', '.jsx'],
  },
  devServer: {
    static: {
      directory: path.join(__dirname, 'dist'),
    },
    // DEV_API_URL: optional target for API proxy (default http://localhost:4096)
    // Use https://localhost:4096 when backend runs with TLS
    proxy: (() => {
      const target = process.env.DEV_API_URL || 'http://localhost:4096'
      return [
        {
          context: ['/api/chat'],
          target,
          changeOrigin: true,
          secure: target.startsWith('https'),
          proxyTimeout: 300000,
          timeout: 300000,
        },
        {
          context: ['**', '!**.js', '!/api/chat'],
          target,
          secure: target.startsWith('https'),
        },
      ]
    })(),
    compress: false
  }
}