import requests
from bs4 import BeautifulSoup
from aip import AipImageClassify
from flask import Flask, jsonify, request
from flask_cors import CORS
import base64
import os
import re